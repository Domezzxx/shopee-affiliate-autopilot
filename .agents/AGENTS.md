# Food Sourcing and Accuracy Rules

1. **Verify Image Contents**: Always double-check that downloaded or generated food images match the traditional appearance of the Thai dish (e.g., Pad Kra Pao should feature holy basil, chili, minced meat/crispy pork, and a fried egg on rice; it must never be confused with desserts, cookies, or other cuisines).
2. **Sourcing Strategy**: 
   * When using Unsplash or other open photo sites, prefer verified direct URLs/IDs. If downloading programmatically, ensure headers bypass default blocks (403 errors).
   * For Thai local dishes, Wikimedia Commons categories (e.g., `Category:Phat_kaphrao` or `Category:Pad_Thai`) are highly reliable sources for public domain, accurate images.
3. **Autopilot Fallback**: If an image is downloaded from an unverified automated script, verify its metadata or fallback to safe locally cached food category stock assets if available.
4. **Text and Image Separation (Unobstructed Food)**:
   * Do not draw text overlays, badges, or buttons directly over the main subject of the food photo (the plate/dish) or the person's face.
   * If a photo has key subjects at the center/bottom, utilize a **Header/Footer Banner Layout** where the image is framed in a clean middle window (e.g., Y=220 to 1020), while all metadata, titles, and CTA buttons are restricted to solid-colored top and bottom panels.

