# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import aiohttp
from PIL import (Image, ImageDraw, ImageEnhance,
                 ImageFilter, ImageFont, ImageOps)

from anony import config
from anony.helpers import Track


class Thumbnail:
    def __init__(self):
        font_path_bold = "anony/helpers/Raleway-Bold.ttf"
        font_path_light = "anony/helpers/Inter-Light.ttf"
        
        self.font_title = ImageFont.truetype(font_path_bold, 60)
        self.font_subtitle = ImageFont.truetype(font_path_light, 35)
        self.font_duration = ImageFont.truetype(font_path_light, 22)
        self.font_now = ImageFont.truetype(font_path_light, 16)
        self.font_logo = ImageFont.truetype(font_path_bold, 26)
        self.font_logo_sub = ImageFont.truetype(font_path_light, 12)
        self.font_btn = ImageFont.truetype(font_path_light, 16)

        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        self.session = aiohttp.ClientSession()
        
    async def close(self) -> None:
        await self.session.close()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with self.session.get(url) as resp:
            with open(output_path, "wb") as f: f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}.png"
            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)
            
            # 1. Album art & Background
            try:
                base_image = Image.open(temp).convert("RGBA")
            except Exception:
                base_image = Image.new("RGBA", size, color="#123d4d")
                
            # Create a glassy, dynamic background
            background = base_image.resize(size, Image.Resampling.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(40))
            overlay = Image.new("RGBA", size, (0, 0, 0, 160))
            image = Image.alpha_composite(background, overlay)
            draw = ImageDraw.Draw(image)

            # Get dominant color
            dom_color_raw = base_image.resize((1, 1)).getpixel((0, 0))
            if len(dom_color_raw) == 4:
                dom_color_raw = dom_color_raw[:3]
            r, g, b = dom_color_raw
            # Make sure it's bright enough
            dom_color = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255))
            text_color = "white"

            # 2. Main Card
            card_box = (60, 80, 1220, 640)
            # Use alpha composite for drawing card to avoid drawing errors on older PIL
            card_overlay = Image.new("RGBA", size, (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_overlay)
            card_draw.rounded_rectangle(card_box, radius=30, fill=(0, 0, 0, 120), outline=(255, 255, 255, 40), width=2)
            image = Image.alpha_composite(image, card_overlay)
            draw = ImageDraw.Draw(image)

            # 3. Album Art Foreground
            album_box = (100, 120, 520, 460)
            album_w = album_box[2] - album_box[0]
            album_h = album_box[3] - album_box[1]
            album = ImageOps.fit(base_image, (album_w, album_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            
            mask = Image.new("L", (album_w, album_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, album_w, album_h), radius=20, fill=255)
            album.putalpha(mask)
            image.paste(album, (album_box[0], album_box[1]), album)

            # 4. Texts
            text_x = 560
            
            # Now Playing
            now_y = 130
            eq_x = text_x
            eq_y = now_y
            draw.rectangle([eq_x, eq_y+4, eq_x+2, eq_y+12], fill=dom_color)
            draw.rectangle([eq_x+4, eq_y, eq_x+6, eq_y+12], fill=dom_color)
            draw.rectangle([eq_x+8, eq_y+6, eq_x+10, eq_y+12], fill=dom_color)
            draw.rectangle([eq_x+12, eq_y+2, eq_x+14, eq_y+12], fill=dom_color)
            draw.text((text_x + 25, now_y - 2), "N O W   P L A Y I N G", font=self.font_now, fill=dom_color)
            
            # Title
            title_text = song.title
            while draw.textlength(title_text + "...", font=self.font_title) > 600:
                title_text = title_text[:-1]
            if len(title_text) < len(song.title):
                title_text += "..."
            draw.text((text_x, 190), title_text, font=self.font_title, fill="white")
            
            # Artist
            artist_text = song.channel_name
            while draw.textlength(artist_text + "...", font=self.font_subtitle) > 600:
                artist_text = artist_text[:-1]
            if len(artist_text) < len(song.channel_name):
                artist_text += "..."
            draw.text((text_x, 270), artist_text, font=self.font_subtitle, fill=dom_color)
            
            # 5. Progress Bar
            bar_y = 420
            bar_w = 580
            bar_x = text_x
            
            draw.line([(bar_x, bar_y), (bar_x + bar_w, bar_y)], fill=(255, 255, 255, 40), width=4)
            # Just 1% filled as requested "Duration 0:01 se suru ho"
            draw.line([(bar_x, bar_y), (bar_x + 6, bar_y)], fill=dom_color, width=4)
            draw.ellipse([(bar_x + 2, bar_y - 6), (bar_x + 14, bar_y + 6)], fill=dom_color)
            
            draw.text((bar_x, bar_y + 15), "0:01", font=self.font_duration, fill=dom_color)
            
            duration_text = song.duration
            try:
                tw = draw.textlength(duration_text, font=self.font_duration)
            except Exception:
                tw = 40
            draw.text((bar_x + bar_w - tw, bar_y + 15), duration_text, font=self.font_duration, fill=dom_color)
            
            # 6. Bottom area
            bottom_y = 560
            
            # Logo
            logo_x = 100
            draw.ellipse([(logo_x, bottom_y-20), (logo_x+40, bottom_y+20)], outline=dom_color, width=2)
            # Instead of a character, draw a simple note
            draw.ellipse((logo_x+12, bottom_y+2, logo_x+18, bottom_y+10), fill=dom_color)
            draw.ellipse((logo_x+24, bottom_y, logo_x+30, bottom_y+8), fill=dom_color)
            draw.line([(logo_x+17, bottom_y+6), (logo_x+17, bottom_y-10), (logo_x+29, bottom_y-12), (logo_x+29, bottom_y+4)], fill=dom_color, width=2)
            draw.line([(logo_x+17, bottom_y-10), (logo_x+29, bottom_y-12)], fill=dom_color, width=3)
            
            draw.text((logo_x+55, bottom_y-18), "YUKKI MUSIC", font=self.font_logo, fill=dom_color)
            draw.line([(logo_x+55, bottom_y+18), (logo_x+80, bottom_y+18)], fill=(255, 255, 255, 100), width=1)
            draw.text((logo_x+85, bottom_y+12), "MUSIC THAT FEELS LIKE YOU", font=self.font_logo_sub, fill=(255, 255, 255, 150))
            draw.line([(logo_x+245, bottom_y+18), (logo_x+270, bottom_y+18)], fill=(255, 255, 255, 100), width=1)
            
            # Controls
            ctrl_x = 600
            # Shuffle icon (simplified)
            draw.line([(ctrl_x, bottom_y-4), (ctrl_x+15, bottom_y+6)], fill=dom_color, width=2)
            draw.line([(ctrl_x, bottom_y+6), (ctrl_x+15, bottom_y-4)], fill=dom_color, width=2)
            draw.polygon([(ctrl_x+15, bottom_y+6), (ctrl_x+18, bottom_y+2), (ctrl_x+11, bottom_y+2)], fill=dom_color)
            draw.polygon([(ctrl_x+15, bottom_y-4), (ctrl_x+18, bottom_y-8), (ctrl_x+11, bottom_y-8)], fill=dom_color)
            
            # Prev
            draw.polygon([(ctrl_x+80, bottom_y-8), (ctrl_x+80, bottom_y+8), (ctrl_x+70, bottom_y)], fill="white")
            draw.line([(ctrl_x+70, bottom_y-8), (ctrl_x+70, bottom_y+8)], fill="white", width=2)
            
            # Play/Pause
            draw.ellipse([(ctrl_x+130, bottom_y-25), (ctrl_x+180, bottom_y+25)], outline=dom_color, width=2)
            draw.line([(ctrl_x+148, bottom_y-10), (ctrl_x+148, bottom_y+10)], fill=dom_color, width=4)
            draw.line([(ctrl_x+162, bottom_y-10), (ctrl_x+162, bottom_y+10)], fill=dom_color, width=4)
            
            # Next
            draw.polygon([(ctrl_x+230, bottom_y-8), (ctrl_x+230, bottom_y+8), (ctrl_x+240, bottom_y)], fill="white")
            draw.line([(ctrl_x+240, bottom_y-8), (ctrl_x+240, bottom_y+8)], fill="white", width=2)
            
            # Repeat icon (simplified)
            draw.line([(ctrl_x+300, bottom_y-4), (ctrl_x+315, bottom_y-4)], fill=dom_color, width=2)
            draw.line([(ctrl_x+300, bottom_y+4), (ctrl_x+315, bottom_y+4)], fill=dom_color, width=2)
            draw.polygon([(ctrl_x+315, bottom_y-4), (ctrl_x+310, bottom_y-8), (ctrl_x+310, bottom_y)], fill=dom_color)
            draw.polygon([(ctrl_x+300, bottom_y+4), (ctrl_x+305, bottom_y+8), (ctrl_x+305, bottom_y)], fill=dom_color)
            
            # Download Button
            btn_w = 140
            btn_h = 40
            btn_x = 1000
            btn_y = bottom_y - 20
            draw.rounded_rectangle([btn_x, btn_y, btn_x+btn_w, btn_y+btn_h], radius=20, outline=dom_color, width=2)
            draw.text((btn_x+20, btn_y+10), "↓ DOWNLOAD", font=self.font_btn, fill=dom_color)
            
            image = image.convert("RGB")
            image.save(output)
            
            try: os.remove(temp)
            except Exception: pass
            
            return output
        except Exception:
            return config.DEFAULT_THUMB

