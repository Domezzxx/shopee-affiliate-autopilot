---
name: ai_food_design
description: Guidelines and prompt formulas for generating high-converting, appetizing AI food photography and creative advertising layouts.
---

# 🎨 Skill: AI Food Design & Photography

This skill defines the professional standard for generating mouth-watering AI food visual assets and composing high-converting social media advertising posters.

---

## 📷 1. The Gold-Standard AI Food Prompt Formula

To generate images that match commercial advertising standards (inspired by Foodshot, Recraft, and Getty Images), use the structured multi-attribute prompt formula:

$$\text{Prompt} = \text{[Subject]} + \text{[Sensory Details]} + \text{[Setting/Surface]} + \text{[Lighting Setup]} + \text{[Composition & Camera]} + \text{[Theme/Style]}$$

### 🔍 Attributes Breakdown:
1. **Subject**: The core Thai menu item with correct ingredients (e.g. *minced pork Pad Kra Pao with holy basil, sliced red chilies, and a crispy fried egg on steamed jasmine rice*).
2. **Sensory Details**: Appeal to taste (e.g. *glistening sauce, hot steam rising, crispy duck egg edges, fresh vibrant basil leaves, moist textures*).
3. **Setting/Surface**: High-contrast, premium backgrounds (e.g. *isolated round black slate plate, warm white marble countertop, rustic dark wooden table*).
4. **Lighting Setup**: Professional photo studio lighting (e.g. *softbox side lighting, cinematic volumetric backlighting, natural warm window light*).
5. **Composition & Camera**: Camera details (e.g. *overhead flat-lay view, macro close-up shot, 45-degree angled 3/4 composition, shallow depth of field, warm bokeh background, 8k commercial photo*).
6. **Theme/Style**: Styling matching the target campaign:
   * **Fine Dining**: Dark moody background, tiny gold flakes, elegant plate decoration.
   * **Delivery & Takeout**: Bright lighting, clean containers, friendly, warm setting.
   * **Studio / Commercial**: Isolated product focus, high contrast, clean shapes.

---

## 🎨 2. Viral Poster Layout Patterns

When combining food images with text overlays (such as titles, rating stars, price, and CTA buttons), alternate between these 4 high-converting layouts:

### A. Neon Street / Dark Grunge Style
*   **Best for**: Spicy, hot, or street-style dishes.
*   **Composition**: Carbon slate dark background, main dish cropped as a floating circle with 3D drop shadow, surrounded by floating sparks/embers, massive semi-transparent background word `SPICY`, and slanted neon sticker badges.

### B. Retro Magazine Collage Style
*   **Best for**: Traditional, nostalgic, or classic recipes.
*   **Composition**: Warm cream checkered grid backdrop, food/person photo framed in a polaroid box with thick offset shadows, masking tape corner stickers, and a bubbly hand-drawn retro font.

### C. Premium Modern Editorial Style
*   **Best for**: Premium, high-quality, and luxury menu items.
*   **Composition**: Deep matte forest green or black canvas, gold double-line border frames, 45/55 clean vertical split layout, and elegant serif typography with generous letter-spacing.

### D. Unobstructed Header/Footer Banner Style
*   **Best for**: Lifestyle food shots featuring customers or chefs.
*   **Composition**: Frames the image in a clean middle window (Y=220 to 1020) without any text overlays. All metadata, headings, ratings, and CTA buttons are restricted to solid-colored top and bottom panels.

---

## 🚫 3. Critical Visual Guardrails

1. **Verify Thai Culinary Accuracy**: Always check that local Thai food items feature traditional ingredients (no green beans/carrots in Kra Pao; boat noodles must have dark rich broth). Wikimedia Commons is the primary reliable public domain source.
2. **Prevent Emoji Rendering Boxes (Tofu)**: Never draw raw unicode emoji characters (e.g., 🌶️, 🍳) inside PIL text overlays on Windows, as they render as empty squares (`□`). Instead, draw clean vector symbols using lines (`d.line`) or use clean alphanumeric characters.
3. **Ensure Legibility**: When text overlays are used, draw soft drop shadows or semi-transparent backing cards to ensure a high-contrast read.
