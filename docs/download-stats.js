const stats = document.querySelector(".download-stats");

if (stats) {
  const countElement = stats.querySelector("[data-download-count]");
  const releasesUrl = "https://api.github.com/repos/bechou0410/canon-lbp2900-macos27-driver/releases?per_page=100";

  const loadDownloadStats = async () => {
    let nextUrl = releasesUrl;
    let downloadCount = 0;

    while (nextUrl) {
      const response = await fetch(nextUrl, {
        headers: { Accept: "application/vnd.github+json" }
      });
      if (!response.ok) throw new Error(`GitHub API returned ${response.status}`);

      const releases = await response.json();
      if (!Array.isArray(releases)) throw new Error("Unexpected GitHub API response");

      for (const release of releases) {
        const installers = (release.assets ?? []).filter((asset) =>
          typeof asset.name === "string" && asset.name.toLowerCase().endsWith(".pkg")
        );
        for (const installer of installers) {
          const assetDownloads = Number(installer.download_count);
          if (Number.isFinite(assetDownloads) && assetDownloads >= 0) downloadCount += assetDownloads;
        }
      }

      const linkHeader = response.headers.get("Link") ?? "";
      nextUrl = linkHeader.match(/<([^>]+)>;\s*rel="next"/)?.[1] ?? "";
    }

    countElement.textContent = new Intl.NumberFormat("vi-VN").format(downloadCount);
  };

  loadDownloadStats().catch(() => {
    countElement.textContent = "—";
  });
}
