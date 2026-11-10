#!/usr/bin/env python3
"""Build an Android ARM64 APK with one explicitly trusted Horizon .hnmod."""
import argparse, hashlib, ipaddress, json, os, re, shutil, socket, subprocess, sys, tomllib, urllib.parse, urllib.request, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "https://github.com/horizon-rust/horizon.git"
MIXINS = "https://github.com/horizon-rust/horizon-mixins"
MAX_BYTES = 64 * 1024 * 1024
REV = re.compile(r"^[0-9a-f]{40}$")
MOD_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def run(args, cwd=ROOT, capture=False):
    args = [str(x) for x in args]
    print("+ " + " ".join(args), flush=True)
    return subprocess.run(args, cwd=cwd, check=True, text=capture,
                          stdout=subprocess.PIPE if capture else None).stdout.strip() if capture else None


def public_https(value):
    p = urllib.parse.urlparse(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Use a public HTTPS .hnmod URL")
    if p.hostname in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Local URLs are not allowed")
    try:
        ip = ipaddress.ip_address(p.hostname)
        if not ip.is_global:
            raise ValueError("Private IP URL refused")
    except ValueError as e:
        if "refused" in str(e):
            raise
    else:
        return value
    for item in socket.getaddrinfo(p.hostname, p.port or 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(item[4][0]).is_global:
            raise ValueError("URL resolves to a private address")
    return value


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        public_https(url)
        return super().redirect_request(req, fp, code, msg, headers, url)


def fetch(url, path):
    request = urllib.request.Request(public_https(url), headers={"User-Agent": "Horizon-Android-Builder"})
    total = 0
    with urllib.request.build_opener(Redirects).open(request, timeout=60) as response, path.open("xb") as out:
        while data := response.read(1024 * 1024):
            total += len(data)
            if total > MAX_BYTES:
                raise ValueError(".hnmod supera il limite di 64 MiB")
            out.write(data)
    if not total:
        raise ValueError("Archivio .hnmod vuoto")
    print("Bundle SHA-256:", hashlib.sha256(path.read_bytes()).hexdigest())


def unpack(path, out):
    out.mkdir(parents=True)
    with zipfile.ZipFile(path) as z:
        entries, names, expanded = z.infolist(), set(), 0
        if not entries or len(entries) > 512:
            raise ValueError("Numero di file .hnmod non valido")
        raw_manifest = None
        for e in entries:
            name, p = e.filename, PurePosixPath(e.filename)
            mode = (e.external_attr >> 16) & 0o170000
            if not name or "\\" in name or p.is_absolute() or any(x in ("", ".", "..") for x in p.parts) or mode == 0o120000 or name in names:
                raise ValueError("Percorso duplicato o non sicuro: " + name)
            names.add(name)
            expanded += e.file_size
            if expanded > MAX_BYTES:
                raise ValueError(".hnmod espanso oltre 64 MiB")
            if name == "horizon-native.json":
                raw_manifest = z.read(e)
        if raw_manifest is None:
            raise ValueError("Manca horizon-native.json")
        m = json.loads(raw_manifest)
        allowed = {"schema", "id", "version", "game", "horizon", "mixins", "hooks"}
        if not isinstance(m, dict) or set(m) - allowed or m.get("schema") != 1:
            raise ValueError("Schema .hnmod non valido o campi sconosciuti")
        mid, horizon, mixins = m.get("id", ""), m.get("horizon", ""), m.get("mixins", "")
        game = m.get("game", "")
        version = m.get("version", "")
        pinned_game = json.loads((ROOT / "research-lock.json").read_text())["minecraft"]["version"]
        if game != pinned_game:
            raise ValueError(f".hnmod targets Minecraft {game!r}, but this Android build targets {pinned_game}")
        if not isinstance(mid, str) or not MOD_ID.fullmatch(mid) or not isinstance(version, str) or not version.strip():
            raise ValueError("ID/version .hnmod non validi")
        if not isinstance(horizon, str) or not REV.fullmatch(horizon) or not isinstance(mixins, str) or not REV.fullmatch(mixins):
            raise ValueError("Revisioni Horizon/horizon-mixins non valide")
        if "hooks" in m and (not isinstance(m["hooks"], int) or isinstance(m["hooks"], bool) or m["hooks"] < 1):
            raise ValueError("Versione hook API non valida")
        manifest_path = f"mixins/{mid}/horizon-mixin.toml"
        if manifest_path not in names:
            raise ValueError("Manifest horizon-mixin.toml mancante")
        mixin_manifest = tomllib.loads(z.read(manifest_path).decode("utf-8"))
        if mixin_manifest.get("mod", {}).get("id") != mid or mixin_manifest.get("mod", {}).get("version") != version:
            raise ValueError("ID/version dei due manifest .hnmod non corrispondono")
        if mixin_manifest.get("compatibility", {}).get("horizon_revision") != horizon:
            raise ValueError("La revisione Horizon non corrisponde nei due manifest")
        unsupported = {"api", "dependencies", "crate", "post_build"} & set(mixin_manifest)
        if unsupported:
            raise ValueError("Questa prima pipeline ARM64 non supporta ancora le funzioni native avanzate: " + ", ".join(sorted(unsupported)))
        injections = mixin_manifest.get("injection", [])
        if any(isinstance(item, dict) and "trait_method" in item for item in injections):
            raise ValueError("Le trait_method richiedono il generatore API nativo, non ancora portato su Android")
        for e in entries:
            if e.is_dir():
                continue
            dest = out.joinpath(*PurePosixPath(e.filename).parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(e) as src, dest.open("xb") as dst:
                shutil.copyfileobj(src, dst)
    return mid, horizon, mixins


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle-url", required=True)
    p.add_argument("--trust-native-code", action="store_true")
    p.add_argument("--sdk", required=True)
    p.add_argument("--java-home", required=True)
    p.add_argument("--gradle", required=True)
    p.add_argument("--ndk-version", default="28.2.13676358")
    p.add_argument("--build-tools-version", default="35.0.0")
    p.add_argument("--dev-version-code", required=True, type=int)
    a = p.parse_args()
    if not a.trust_native_code:
        p.error("Il codice .hnmod non è sandboxed: serve il consenso esplicito --trust-native-code")
    work = ROOT.parent / (ROOT.name + "-android-native-work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    archive, bundle = work / "input.hnmod", work / "bundle"
    fetch(a.bundle_url, archive)
    mid, revision, mixins = unpack(archive, bundle)
    print(f"Mod {mid}; Horizon {revision}; horizon-mixins {mixins}", flush=True)

    head = run(["git", "rev-parse", "HEAD"], capture=True)
    run(["git", "fetch", "--no-tags", UPSTREAM, revision])
    if subprocess.run(["git", "merge-base", "--is-ancestor", revision, head], cwd=ROOT).returncode:
        raise RuntimeError("La revisione Horizon della mod non è antenata del fork Android: porting non applicabile in sicurezza")
    patch = subprocess.check_output(["git", "diff", "--binary", revision, head], cwd=ROOT)
    source = work / "source"
    run(["git", "worktree", "add", "--detach", source, revision])
    try:
        if patch:
            subprocess.run(["git", "apply", "--binary", "-"], cwd=source, input=patch, check=True)
        patched, toolroot = work / "patched", work / "mixins-tool"
        tool = toolroot / "bin/horizon-mixins"
        run(["cargo", "install", "--locked", "--git", MIXINS, "--rev", mixins, "--root", toolroot, "horizon-mixins-cli"])
        run([tool, "apply", "--workspace", source, "--mods", bundle / "mixins", "--out", patched])
        if not (patched / "tools/android_build.py").is_file():
            raise RuntimeError("Il sorgente risultante non contiene il builder Android")
        run([sys.executable, patched / "tools/android_prepare.py"], cwd=patched)
        apk = patched / ".local/android/apk/arm64-v8a/horizon-android-public.apk"
        run([sys.executable, patched / "tools/android_build.py", "--abi", "arm64-v8a",
             "--sdk", a.sdk, "--java-home", a.java_home, "--gradle", a.gradle,
             "--ndk-version", a.ndk_version, "--build-tools-version", a.build_tools_version,
             "--public", "--dev-build", "hnmod", "--dev-version-code", a.dev_version_code], cwd=patched)
        if not apk.is_file():
            raise RuntimeError("APK ARM64 non prodotto")
        result = ROOT / "horizon-android-hnmod-arm64.apk"
        shutil.copy2(apk, result)
        metadata = {
            "schema": 1,
            "package_id": "dev.horizon.android.dev",
            "abi": "arm64-v8a",
            "mod_id": mid,
            "bundle_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "apk_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
            "horizon_revision": revision,
            "horizon_mixins_revision": mixins,
            "android_fork_commit": head,
            "rust_toolchain": "1.95.0",
            "ndk_version": a.ndk_version,
            "build_tools_version": a.build_tools_version,
        }
        (ROOT / "horizon-android-hnmod-arm64.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        print("APK pronto:", result, flush=True)
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(source)], cwd=ROOT, check=False)


if __name__ == "__main__":
    main()
