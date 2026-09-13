/**
 * Computes the SHA-256 hex digest of a File or Blob using native Web Crypto API.
 */
export async function computeFileHash(file: File | Blob): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hexDigest = hashArray
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return hexDigest;
}
