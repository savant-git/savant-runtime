export const ASSETS = {
  approvedLogo: "/cinematic/savant-logo.glb",
  approvedLogoSourceRequired: "assets/source/savant-logo.glb",
} as const;

export async function approvedLogoExists(
  signal?: AbortSignal,
): Promise<boolean> {
  try {
    const response = await fetch(ASSETS.approvedLogo, {
      method: "HEAD",
      signal,
      cache: "force-cache",
    });
    return (
      response.ok &&
      response.headers.get("content-type")?.includes("model") === true
    );
  } catch {
    return false;
  }
}
