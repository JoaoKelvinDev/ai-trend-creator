"""Clustering de tendências - Agrupa tendências similares por similaridade textual."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.db.models import TrendCluster, TrendClusterItem, TrendItem
from backend.app.db.session import get_db_context

logger = logging.getLogger(__name__)


class TrendClusterer:
    """Agrupa tendências similares em clusters usando TF-IDF + cosine similarity."""

    def __init__(self, similarity_threshold: float = 0.3, min_cluster_size: int = 1):
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size

    async def cluster_trends(self, trend_ids: list[UUID] | None = None) -> int:
        """
        Executa clustering nas tendências.

        Args:
            trend_ids: IDs específicos para clusterizar. Se None, clusteriza todas sem cluster.

        Returns:
            Número de clusters criados/atualizados.
        """
        async with get_db_context() as db:
            # Buscar trends que não estão em cluster ou todos se trend_ids fornecido
            if trend_ids:
                query = TrendItem.__table__.select().where(TrendItem.id.in_(trend_ids))
            else:
                # Buscar trends sem cluster
                subq = TrendClusterItem.__table__.select().with_only_columns(TrendClusterItem.trend_item_id)
                query = TrendItem.__table__.select().where(~TrendItem.id.in_(subq))

            result = await db.execute(query)
            trends = result.mappings().all()

            if len(trends) < self.min_cluster_size:
                logger.info("Poucas tendências para clustering", extra={"count": len(trends)})
                return 0

            # Preparar textos para TF-IDF
            texts = []
            trend_data = []
            for t in trends:
                text = f"{t.title} {t.niche_guess or ''}"
                texts.append(text)
                trend_data.append({
                    "id": t["id"],
                    "title": t["title"],
                    "niche_guess": t["niche_guess"],
                    "provider": t["provider"],
                })

            # Stop words em português (customizado já que sklearn não tem built-in)
            pt_stop_words = [
                "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
                "em", "no", "na", "nos", "nas", "por", "para", "com", "sem", "sob", "sobre",
                "e", "ou", "mas", "que", "se", "como", "mais", "menos", "muito", "pouco",
                "todo", "toda", "todos", "todas", "este", "esta", "estes", "estas", "esse",
                "essa", "esses", "essas", "aquele", "aquela", "aqueles", "aquelas", "isto",
                "isso", "aquilo", "meu", "minha", "meus", "minhas", "seu", "sua", "seus",
                "suas", "nosso", "nossa", "nossos", "nossas", "deles", "delas", "lhe", "lhes",
                "me", "te", "nos", "vos", "lhe", "lhes", "si", "consigo", "onde", "quando",
                "porque", "pois", "logo", "portanto", "entao", "assim", "tambem", "ja",
                "ainda", "sempre", "nunca", "tudo", "nada", "algo", "alguem", "ninguem",
                "cada", "qual", "quais", "quanto", "quantos", "quantas", "qual", "quais"
            ]

            # Calcular similaridade
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=pt_stop_words,
                ngram_range=(1, 2),
                min_df=1,
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)

            # Agrupar por similaridade (algoritmo guloso simples)
            clusters = self._greedy_cluster(similarity_matrix, trend_data)

            # Persistir clusters
            clusters_created = 0
            for cluster_trends in clusters:
                if len(cluster_trends) < self.min_cluster_size:
                    continue

                # Criar cluster
                cluster_title = self._generate_cluster_title(cluster_trends)
                cluster_key = self._generate_cluster_key(cluster_trends)

                cluster = TrendCluster(
                    cluster_key=cluster_key,
                    title=cluster_title,
                    niche_id=None,  # TODO: inferir niche
                )
                db.add(cluster)
                await db.flush()

                # Associar trends ao cluster
                for td in cluster_trends:
                    cluster_item = TrendClusterItem(
                        cluster_id=cluster.id,
                        trend_item_id=td["id"],
                    )
                    db.add(cluster_item)

                clusters_created += 1

            await db.commit()
            logger.info("Clustering concluído", extra={"clusters_created": clusters_created, "trends_processed": len(trends)})
            return clusters_created

    def _greedy_cluster(
        self, similarity_matrix: np.ndarray, trend_data: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Agrupamento guloso baseado em similaridade."""
        n = len(trend_data)
        assigned = [False] * n
        clusters = []

        for i in range(n):
            if assigned[i]:
                continue

            # Iniciar novo cluster com trend i
            cluster = [trend_data[i]]
            assigned[i] = True

            # Encontrar trends similares
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                if similarity_matrix[i, j] >= self.similarity_threshold:
                    cluster.append(trend_data[j])
                    assigned[j] = True

            clusters.append(cluster)

        return clusters

    def _generate_cluster_title(self, cluster_trends: list[dict[str, Any]]) -> str:
        """Gera título representativo do cluster."""
        # Usar o título da trend com mais palavras (mais descritivo)
        longest = max(cluster_trends, key=lambda t: len(t["title"].split()))
        return longest["title"][:200]

    def _generate_cluster_key(self, cluster_trends: list[dict[str, Any]]) -> str:
        """Gera chave única para o cluster baseada nos IDs."""
        ids = sorted(str(t["id"]) for t in cluster_trends)
        import hashlib
        return hashlib.sha256("|".join(ids).encode()).hexdigest()[:32]


async def run_clustering_use_case(trend_ids: list[UUID] | None = None) -> int:
    """Caso de uso para executar clustering."""
    clusterer = TrendClusterer()
    return await clusterer.cluster_trends(trend_ids)