"""Prepare the audited CasADi 3.8.1 core for this application.

Remove optional solvers/dependencies excluded by the license audit and archive
legal notices. Run only in the dedicated virtual environment after installation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

VERSAO = "3.8.1"
MARCADOR = "contorno_core_manifest.json"
PASTA_LEGAL = "contorno_legal"
ESQUEMA = 1


def _localizar() -> Path:
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Use the dedicated .venv Python. Global Python will not be modified.")
    dist = importlib.metadata.distribution("casadi")
    if dist.version != VERSAO:
        raise RuntimeError(
            f"CasADi {dist.version} was not audited by this preparer; expected {VERSAO}. "
            "Reinstall requirements.txt or audit the new version."
        )
    pacote = Path(dist.locate_file("casadi")).resolve()
    if not pacote.is_relative_to(Path(sys.prefix).resolve()) or not pacote.is_dir():
        raise RuntimeError("CasADi is outside the virtual environment; preparation refused.")
    if sys.platform not in {"darwin", "linux", "win32"}:
        raise RuntimeError(f"Unsupported platform: {sys.platform}.")
    return pacote


def _permitido(nome: str) -> bool:
    if nome in {"__init__.py", "casadi.py", "casadi.pyi", "__init__.pyi", "py.typed"}:
        return True
    if re.fullmatch(r"_casadi(?:\.[A-Za-z0-9_-]+)*\.(?:so|pyd)", nome):
        return True
    if sys.platform == "darwin":
        # libc++ é um runtime LLVM necessário, não um plugin otimizador.
        return bool(re.fullmatch(r"libcasadi(?:\.\d+)*\.dylib", nome)) or nome == "libc++.1.0.dylib"
    if sys.platform == "linux":
        return bool(re.fullmatch(r"libcasadi\.so(?:\.\d+)*", nome)) or bool(
            re.fullmatch(r"(?:libstdc\+\+\.so(?:\.\d+)*|libgcc_s\.so(?:\.\d+)*)", nome)
        )
    return nome in {
        "casadi.dll", "libcasadi.dll", "libstdc++-6.dll", "libgcc_s_seh-1.dll",
        "libgcc_s_sjlj-1.dll", "libwinpthread-1.dll",
    }


def _hash(arquivo: Path) -> str:
    h = hashlib.sha256()
    with arquivo.open("rb") as handle:
        for bloco in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _itens_nao_permitidos(pacote: Path) -> list[Path]:
    return [
        item for item in pacote.iterdir()
        if item.name not in {MARCADOR, PASTA_LEGAL, "__pycache__"} and not _permitido(item.name)
    ]


def verificar_instalacao() -> dict[str, Any]:
    """Confere versão, conteúdo e hashes sem importar o kernel ou otimizadores."""
    return verificar_pacote(_localizar())


def verificar_pacote(pacote: Path) -> dict[str, Any]:
    """Verify an explicitly selected core, including an app-owned hosted copy."""
    pacote = pacote.resolve()
    caminho = pacote / MARCADOR
    if not caminho.is_file():
        raise RuntimeError("Mandatory preparation missing. Run: python scripts/preparar_casadi.py")
    try:
        info = json.loads(caminho.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise RuntimeError("Invalid CasADi manifest; run preparation again.") from exc
    if info.get("schema") != ESQUEMA or info.get("version") != VERSAO or info.get("platform") != sys.platform:
        raise RuntimeError("CasADi manifest is incompatible with this installation.")
    restos = _itens_nao_permitidos(pacote)
    if restos:
        raise RuntimeError(
            "CasADi contains optional components outside the audited selection: "
            + ", ".join(p.name for p in restos[:5])
            + ". Run python scripts/preparar_casadi.py again after installing packages."
        )
    registrados = info.get("retained_files", {})
    atuais = {p.name for p in pacote.iterdir() if p.is_file() and _permitido(p.name)}
    if set(registrados) != atuais:
        raise RuntimeError("CasADi core contents changed; repeat preparation.")
    for nome, digest in registrados.items():
        arquivo = pacote / nome
        if not arquivo.is_file() or not arquivo.resolve().is_relative_to(pacote) or _hash(arquivo) != digest:
            raise RuntimeError(f"Changed or external CasADi file: {nome}; repeat preparation.")
    if not info.get("core_import_test_passed"):
        raise RuntimeError("Preparation did not complete the import test.")
    return info


def preparar() -> dict[str, Any]:
    pacote = _localizar()
    if "casadi" in sys.modules:
        raise RuntimeError("Run preparation in a fresh process before importing CadQuery/CasADi.")
    essenciais = [p for p in pacote.iterdir() if p.is_file() and _permitido(p.name)]
    if not {"__init__.py", "casadi.py"}.issubset(p.name for p in essenciais):
        raise RuntimeError("The wheel lacks the expected Python structure; no files were removed.")
    if not any(p.name.startswith("_casadi.") for p in essenciais):
        raise RuntimeError("CasADi native binding not found; no files were removed.")
    legal = pacote / PASTA_LEGAL
    legal.mkdir(exist_ok=True)
    avisos: list[dict[str, str]] = []
    for arquivo in list(pacote.rglob("*")):
        if not arquivo.is_file() or legal in arquivo.parents:
            continue
        if any(termo in arquivo.name.upper() for termo in ("LICENSE", "COPYING", "NOTICE", "COPYRIGHT")):
            if not arquivo.resolve().is_relative_to(pacote):
                raise RuntimeError(f"Legal notice points outside the package: {arquivo}")
            relativo = arquivo.relative_to(pacote)
            destino = legal / relativo
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(arquivo, destino)
            avisos.append({"original_path": relativo.as_posix(), "sha256": _hash(destino)})
    removidos: list[str] = []
    for item in _itens_nao_permitidos(pacote):
        removidos.append(item.name)
        if item.is_symlink() or item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
        else:
            raise RuntimeError(f"Unexpected file type: {item}")
    # Cache antigo não faz parte do núcleo selecionado; Python o recria.
    cache = pacote / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache)
    (legal / "LEIA-ME.txt").write_text(
        "Textos legais originais arquivados antes de excluir plugins, headers e bibliotecas opcionais.\n"
        "A presença de um aviso não significa que o componente foi mantido.\n"
        "METIS/COIN/IPOPT/MUMPS e todos os solvers/plugins CasADi foram excluídos.\n"
        "O núcleo CasADi permanece LGPL-3.0-or-later. A seleção inclui apenas seu binding,\n"
        "biblioteca principal e, quando necessário, runtime C++ LLVM/GCC.\n"
        "Os arquivos dist-info do pip conservam os metadados da wheel original; para a\n"
        "composição real consulte ../contorno_core_manifest.json e os arquivos presentes.\n",
        encoding="utf-8",
    )
    anterior: dict[str, Any] = {}
    marcador = pacote / MARCADOR
    if marcador.is_file():
        try:
            anterior = json.loads(marcador.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    info = {
        "schema": ESQUEMA,
        "version": VERSAO,
        "platform": sys.platform,
        "selection": "core-only-no-optional-solvers",
        "retained_files": {p.name: _hash(p) for p in essenciais},
        "removed_top_level": sorted(set(removidos + anterior.get("removed_top_level", []))),
        "archived_notices": avisos or anterior.get("archived_notices", []),
        "core_import_test_passed": False,
    }
    marcador.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", "import casadi as c; assert float(c.DM(2)+3)==5; print(c.__version__)"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if resultado.returncode:
        raise RuntimeError(
            "The selected core did not import on this platform. No solver was retained. "
            "Audit the native runtime before using the application.\n" + resultado.stderr[-3000:]
        )
    info["core_import_test_passed"] = True
    marcador.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return verificar_instalacao()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="Only verify the existing preparation.")
    args = parser.parse_args()
    try:
        info = verificar_instalacao() if args.verificar else preparar()
    except (RuntimeError, importlib.metadata.PackageNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"CasADi preparation: {exc}", file=sys.stderr)
        return 1
    print(
        f"CasADi {info['version']}: core verified, {len(info['retained_files'])} files, "
        f"{len(info['removed_top_level'])} optional items removed; solvers unavailable."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
