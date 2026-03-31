#!/usr/bin/env python3
"""
roblox_uploader.py — Upload shirts to Roblox via API
Extracts Chrome cookie and uploads directly.
"""
import os, sys, json, shutil, sqlite3, base64, time, ctypes, ctypes.wintypes, struct

# ── DPAPI Decryption (Windows native) ──────────────────────────────────
class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                 ("pbData", ctypes.POINTER(ctypes.c_char))]

def dpapi_decrypt(encrypted):
    blob_in = DATA_BLOB(len(encrypted), ctypes.create_string_buffer(encrypted, len(encrypted)))
    blob_out = DATA_BLOB()
    if ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return data
    return None

def get_chrome_key():
    """Get AES key from Chrome Local State, decrypted via DPAPI."""
    local_state_path = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Google", "Chrome", "User Data", "Local State"
    )
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # Remove "DPAPI" prefix (5 bytes)
    encrypted_key = encrypted_key[5:]
    return dpapi_decrypt(encrypted_key)

def decrypt_cookie(encrypted_value, key):
    """Decrypt Chrome cookie value using AES-256-GCM."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        # v10/v20 format: version(3) + nonce(12) + ciphertext + tag(16)
        nonce = encrypted_value[3:15]
        ciphertext_with_tag = encrypted_value[15:]
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return decrypted.decode("utf-8")
    except ImportError:
        # Fallback: try pycryptodome
        try:
            from Crypto.Cipher import AES
            nonce = encrypted_value[3:15]
            ciphertext = encrypted_value[15:-16]
            tag = encrypted_value[-16:]
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
        except ImportError:
            print("ERROR: Need 'cryptography' or 'pycryptodome' package")
            print("Run: pip install cryptography")
            sys.exit(1)

def get_roblox_cookie():
    """Extract .ROBLOSECURITY cookie from Chrome."""
    key = get_chrome_key()
    if not key:
        print("ERROR: Failed to get Chrome encryption key")
        sys.exit(1)
    
    # Open Chrome cookies DB using SQLite immutable mode (bypasses file lock)
    cookies_path = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Google", "Chrome", "User Data", "Default", "Network", "Cookies"
    )
    # Convert to forward slashes for URI and URL-encode spaces
    uri_path = cookies_path.replace("\\", "/").replace(" ", "%20")
    db_uri = f"file:///{uri_path}?mode=ro&nolock=1&immutable=1"
    print(f"  DB URI: {db_uri}")

    conn = sqlite3.connect(db_uri, uri=True)
    cursor = conn.execute(
        "SELECT encrypted_value FROM cookies WHERE host_key='.roblox.com' AND name='.ROBLOSECURITY'"
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("ERROR: .ROBLOSECURITY cookie not found in Chrome")
        sys.exit(1)
    
    cookie = decrypt_cookie(row[0], key)
    print(f"  Cookie extracted: ...{cookie[-20:]}")
    return cookie

# ── Roblox Upload ──────────────────────────────────────────────────────
import urllib.request, urllib.error

def get_csrf_token(cookie):
    """Get CSRF token from Roblox."""
    req = urllib.request.Request(
        "https://auth.roblox.com/v2/logout",
        method="POST",
        headers={"Cookie": f".ROBLOSECURITY={cookie}"}
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        token = e.headers.get("x-csrf-token", "")
        if token:
            return token
    return None

def upload_shirt(cookie, csrf, image_path, title, description):
    """Upload a shirt to Roblox."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    # Build multipart form data
    request_json = json.dumps({
        "assetType": "Shirt",
        "displayName": title,
        "description": description,
        "creationContext": {
            "creator": {"userId": "1647274201"}
        }
    })
    
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="request"\r\n'
        f"Content-Type: application/json\r\n\r\n"
        f"{request_json}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="fileContent"; filename="shirt.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + image_data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    req = urllib.request.Request(
        "https://apis.roblox.com/assets/user-auth/v1/assets",
        data=body,
        method="POST",
        headers={
            "Cookie": f".ROBLOSECURITY={cookie}",
            "x-csrf-token": csrf,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
    )
    
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read().decode())
        return True, result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.readable() else str(e)
        # CSRF might have expired
        if e.code == 403:
            return False, "CSRF_EXPIRED"
        return False, f"HTTP {e.code}: {error_body}"

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(base_dir, "upload_manifest.json")
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"\n{'='*60}")
    print(f"  ROBLOX SHIRT UPLOADER")
    print(f"  {len(manifest)} shirts to upload")
    print(f"{'='*60}")
    
    # Step 1: Extract cookie
    print("\n[1/3] Extracting Chrome cookie...")
    cookie = get_roblox_cookie()
    
    # Step 2: Get CSRF token
    print("[2/3] Getting CSRF token...")
    csrf = get_csrf_token(cookie)
    if not csrf:
        print("ERROR: Failed to get CSRF token")
        sys.exit(1)
    print(f"  CSRF: {csrf[:10]}...")
    
    # Step 3: Upload shirts
    print(f"[3/3] Uploading {len(manifest)} shirts...\n")
    
    results = []
    description = "Exclusive design by Conundrum by Este | 626Labs"
    
    for i, item in enumerate(manifest):
        file_path = os.path.join(base_dir, item["file"])
        title = item["title"]
        
        if not os.path.exists(file_path):
            print(f"  [{i+1}/{len(manifest)}] SKIP - File not found: {item['file']}")
            results.append({"title": title, "status": "missing"})
            continue
        
        print(f"  [{i+1}/{len(manifest)}] Uploading: {title}...", end=" ", flush=True)
        
        success, resp = upload_shirt(cookie, csrf, file_path, title, description)
        
        if not success and resp == "CSRF_EXPIRED":
            # Refresh CSRF and retry
            csrf = get_csrf_token(cookie)
            if csrf:
                success, resp = upload_shirt(cookie, csrf, file_path, title, description)
        
        if success:
            asset_id = resp.get("assetId", resp.get("id", "unknown"))
            print(f"OK (ID: {asset_id})")
            results.append({"title": title, "status": "uploaded", "assetId": str(asset_id), "response": resp})
        else:
            print(f"FAILED: {resp}")
            results.append({"title": title, "status": "failed", "error": str(resp)})
        
        # Rate limit: 2 second delay between uploads
        if i < len(manifest) - 1:
            time.sleep(2)
    
    # Save results
    results_path = os.path.join(base_dir, "upload_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    uploaded = sum(1 for r in results if r["status"] == "uploaded")
    failed = sum(1 for r in results if r["status"] == "failed")
    
    print(f"\n{'='*60}")
    print(f"  DONE: {uploaded} uploaded, {failed} failed")
    print(f"  Results saved to: {results_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
