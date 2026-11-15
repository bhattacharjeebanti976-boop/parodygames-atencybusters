# PARODY GAMES BY LATENCY BUSTERS

A responsive, static arcade portal designed for GitHub Pages. The original archive contained ten Python games; most use Tkinter, which browsers cannot run directly. This site includes browser-playable JavaScript adaptations of the ten game concepts and retains the supplied artwork/audio files in `assets/`.

## Publish with GitHub Pages
1. Create a GitHub repository (for example `parody-games`).
2. Upload **all files and folders** from this project. Keep `index.html`, `style.css`, `app.js`, and `assets/` together in the repository root.
3. Open **Settings → Pages**.
4. Under **Build and deployment**, choose **Deploy from a branch**, select `main` and `/ (root)`, then Save.
5. Wait for GitHub Pages to publish the site.

## Notes
- No build step or server is required; this is a static website.
- The ten games are browser adaptations, not direct execution of the original `.py` programs. Original source files are preserved alongside their assets in `assets/` for reference.
- The UPI button uses `7001536469@fam`. The QR image is generated on demand by QRServer and needs an internet connection. UPI payment apps handle the payment; the website does not collect or verify payments.
- The Google Fonts stylesheet is optional; system fonts remain as fallback.
