#!/usr/bin/env python
"""Script de diagnóstico do ambiente - Etapa 0 do AGENTS.md."""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    """Executa comando e retorna (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=30)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", "not found"
    except Exception as e:
        return -1, "", str(e)


def check_python() -> dict:
    """Verifica versão do Python."""
    return {
        "version": sys.version.split()[0],
        "executable": sys.executable,
        "version_info": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


def check_ffmpeg() -> dict:
    """Verifica FFmpeg."""
    code, out, err = run_cmd(["ffmpeg", "-version"])
    if code == 0:
        lines = out.split("\n")
        version_line = lines[0] if lines else "unknown"
        return {"available": True, "version": version_line}
    # Tentar via winget no Windows
    code, out, _ = run_cmd(["winget", "list", "ffmpeg"])
    if code == 0 and "FFmpeg" in out:
        return {"available": False, "installable_via_winget": True, "info": out[:200]}
    return {"available": False, "error": err or "not found"}


def check_ollama() -> dict:
    """Verifica Ollama."""
    code, out, err = run_cmd(["ollama", "--version"])
    if code == 0:
        return {"available": True, "version": out}
    code, out, _ = run_cmd(["winget", "list", "ollama"])
    if code == 0 and "Ollama" in out:
        return {"available": False, "installable_via_winget": True}
    return {"available": False, "error": err or "not found"}


def check_comfyui() -> dict:
    """Verifica ComfyUI."""
    code, out, _ = run_cmd(["winget", "list", "comfyui"])
    if code == 0 and "ComfyUI" in out:
        return {"available": False, "installable_via_winget": True, "info": out[:200]}
    return {"available": False, "note": "Verificar instalação manual ou via WSL2"}


def check_piper() -> dict:
    """Verifica Piper TTS."""
    # Verificar se binário existe localmente
    piper_paths = [
        Path("./bin/piper"),
        Path("~/bin/piper").expanduser(),
        Path("/usr/local/bin/piper"),
    ]
    for p in piper_paths:
        if p.exists():
            code, out, _ = run_cmd([str(p), "--help"])
            if code == 0:
                return {"available": True, "path": str(p), "version": out.split("\n")[0]}
    return {"available": False, "note": "Build manual necessário (OHF-Voice/piper1-gpl)"}


def check_gpu() -> dict:
    """Verifica GPU NVIDIA."""
    code, out, err = run_cmd(["nvidia-smi"])
    if code == 0:
        lines = out.split("\n")
        gpu_info = {}
        for line in lines:
            if "NVIDIA GeForce" in line or "NVIDIA RTX" in line:
                gpu_info["name"] = line.strip()
            if "CUDA Version" in line:
                gpu_info["cuda_version"] = line.split("CUDA Version:")[-1].split()[0]
            if "Driver Version" in line:
                gpu_info["driver_version"] = line.split("Driver Version:")[-1].split()[0]
            if "MiB /" in line and "GPU Memory" not in line:
                parts = line.split("|")
                if len(parts) > 2:
                    mem = parts[2].strip()
                    gpu_info["vram"] = mem
        return {"available": True, **gpu_info}
    return {"available": False, "error": err or "nvidia-smi not found"}


def check_docker() -> dict:
    """Verifica Docker."""
    code, out, err = run_cmd(["docker", "--version"])
    if code == 0:
        return {"available": True, "version": out}
    return {"available": False, "error": err}


def check_wsl2() -> dict:
    """Verifica WSL2."""
    code, out, err = run_cmd(["wsl", "--status"])
    if code == 0:
        return {"available": True, "status": out[:500]}
    return {"available": False, "error": err}


def check_disk_space() -> dict:
    """Verifica espaço em disco."""
    try:
        usage = shutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
        return {
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "free_percent": round(usage.free / usage.total * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def check_ram() -> dict:
    """Verifica RAM."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent_used": mem.percent,
        }
    except ImportError:
        return {"error": "psutil não instalado"}
    except Exception as e:
        return {"error": str(e)}


def check_python_packages() -> dict:
    """Verifica pacotes Python essenciais."""
    packages = [
        "fastapi", "uvicorn", "pydantic", "pydantic-settings",
        "sqlalchemy", "alembic", "psycopg", "redis",
        "celery", "httpx", "python-dotenv", "python-json-logger",
        "ffmpeg-python", "python-jose", "passlib", "apscheduler",
    ]
    results = {}
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_"))
            results[pkg] = "installed"
        except ImportError:
            results[pkg] = "missing"
    return results


def main():
    print("[AI Trend Creator] Diagnóstico de Ambiente (Etapa 0)")
    print("=" * 60)

    results = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": check_python(),
        },
        "tools": {
            "ffmpeg": check_ffmpeg(),
            "ollama": check_ollama(),
            "comfyui": check_comfyui(),
            "piper": check_piper(),
        },
        "hardware": {
            "gpu": check_gpu(),
            "disk": check_disk_space(),
            "ram": check_ram(),
        },
        "infrastructure": {
            "docker": check_docker(),
            "wsl2": check_wsl2(),
        },
        "python_packages": check_python_packages(),
    }

    # Imprimir resumo
    print("\n[RESUMO]")
    print(f"  OS: {results['platform']['system']} {results['platform']['release']}")
    print(f"  Python: {results['platform']['python']['version']}")
    gpu_status = 'OK' if results['hardware']['gpu'].get('available') else 'NAO'
    print(f"  GPU: {gpu_status} {results['hardware']['gpu'].get('name', 'N/A')}")
    print(f"  VRAM: {results['hardware']['gpu'].get('vram', 'N/A')}")
    print(f"  RAM: {results['hardware']['ram'].get('total_gb', 'N/A')} GB total")
    print(f"  Disco livre: {results['hardware']['disk'].get('free_gb', 'N/A')} GB")
    ffmpeg_status = 'OK' if results['tools']['ffmpeg'].get('available') else 'NAO'
    print(f"  FFmpeg: {ffmpeg_status}")
    ollama_status = 'OK' if results['tools']['ollama'].get('available') else 'NAO'
    print(f"  Ollama: {ollama_status}")
    comfyui_status = 'OK' if results['tools']['comfyui'].get('available') else 'NAO'
    print(f"  ComfyUI: {comfyui_status}")
    piper_status = 'OK' if results['tools']['piper'].get('available') else 'NAO'
    print(f"  Piper: {piper_status}")
    docker_status = 'OK' if results['infrastructure']['docker'].get('available') else 'NAO'
    print(f"  Docker: {docker_status}")
    wsl2_status = 'OK' if results['infrastructure']['wsl2'].get('available') else 'NAO'
    print(f"  WSL2: {wsl2_status}")

    # Determinar perfil recomendado
    gpu_ok = results['hardware']['gpu'].get('available', False)
    vram_str = results['hardware']['gpu'].get('vram', '0 MiB')
    vram_mib = 0
    if 'MiB' in vram_str:
        try:
            vram_mib = int(vram_str.split()[0].replace(',', ''))
        except:
            pass

    print("\n[PERFIL RECOMENDADO]")
    if gpu_ok and vram_mib >= 6000:
        print("  Perfil B — GPU compatível (VRAM >= 6GB)")
        print("  -> ComfyUI com checkpoint FP16 viavel")
        print("  -> Ollama 7B-8B quantizado viavel")
    elif gpu_ok and vram_mib >= 4000:
        print("  Perfil A/B limite — GPU com VRAM limitada (4-6GB)")
        print("  -> ComfyUI apenas SD1.5 ou SDXL FP16 otimizado")
        print("  -> Ollama 7B quantizado viavel")
    else:
        print("  Perfil A — Sem GPU apropriada / VRAM insuficiente")
        print("  -> LLM pequeno quantizado via Ollama")
        print("  -> Geracao visual: templates/programatica")
        print("  -> ComfyUI apenas CPU (muito lento) se explicitamente solicitado")

    # Salvar JSON completo
    output_path = Path("diagnosis.json")
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n[OK] Relatorio completo salvo em: {output_path}")

    return results


if __name__ == "__main__":
    main()