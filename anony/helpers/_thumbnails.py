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
        self.fill = (255, 255, 255)
        
        font_path_bold = "anony/helpers/Raleway-Bold.ttf"
        font_path_light = "anony/helpers/Inter-Light.ttf"
        
        self.font_title = ImageFont.truetype(font_path_bold, 65)
        self.font_subtitle = ImageFont.truetype(font_path_light, 45)
        self.font_para = ImageFont.truetype(font_path_light, 24)
        self.font_btn = ImageFont.truetype(font_path_bold, 35)

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
            album_size = (450, 450)
            try:
                base_image = Image.open(temp).convert("RGBA")
            except Exception:
                base_image = Image.new("RGBA", size, color="#123d4d")
                
            # Create a glassy, dynamic background
            background = base_image.resize(size, Image.Resampling.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(40))
            # Dark overlay for better text readability
            overlay = Image.new("RGBA", size, (0, 0, 0, 160)) 
            image = Image.alpha_composite(background, overlay)
            draw = ImageDraw.Draw(image)

            # Process album for the foreground
            album = ImageOps.fit(base_image, album_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                
            # Draw rounded corners for album
            mask = Image.new("L", album_size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0) + album_size, radius=40, fill=255)
            album.putalpha(mask)
            image.paste(album, (80, 80), album)

            # 2. Text
            title_x = 580
            title_y = 120
            # Truncate title
            title_text = song.title[:20] + "..." if len(song.title) > 20 else song.title
            artist_text = song.channel_name[:20] + "..." if len(song.channel_name) > 20 else song.channel_name
            
            draw.text((title_x, title_y), title_text, font=self.font_title, fill="white")
            draw.text((title_x, title_y + 85), artist_text, font=self.font_subtitle, fill="#a0c0c7")
            
            views = f"Views: {song.view_count}"
            duration = f"Duration: {song.duration}"
            requested = f"Requested by: {song.user}"
            
            para_text = f"• {views}\n• {duration}\n• {requested}"
            draw.text((title_x, title_y + 180), para_text, font=self.font_para, fill="#7b9aa3", spacing=10)


            # Get dominant color
            dom_color = base_image.resize((1, 1)).getpixel((0, 0))
            if len(dom_color) == 4:
                dom_color = dom_color[:3]
            
            # Boost dominant color brightness for button
            r, g, b = dom_color
            btn_color = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255))
            text_color = "white" if (r*0.299 + g*0.587 + b*0.114) < 150 else "black"

            # 4. Controls
            control_y = 600
            control_x_start = 125
            spacing = 110
            radius = 38
            
            for i in range(4):
                cx = control_x_start + i * spacing
                fill_color = "white" if i == 2 else (255, 255, 255, 40)
                draw.ellipse((cx-radius, control_y-radius, cx+radius, control_y+radius), fill=fill_color)
                
                # draw icons
                icon_color = "white" if i != 2 else "black"
                if i == 0: # prev
                    draw.polygon([(cx+8, control_y-12), (cx+8, control_y+12), (cx-8, control_y)], fill=icon_color)
                    draw.line([(cx-8, control_y-12), (cx-8, control_y+12)], fill=icon_color, width=4)
                elif i == 1: # play
                    draw.polygon([(cx-5, control_y-14), (cx-5, control_y+14), (cx+12, control_y)], fill=icon_color)
                elif i == 2: # next
                    draw.polygon([(cx-8, control_y-12), (cx-8, control_y+12), (cx+8, control_y)], fill=icon_color)
                    draw.line([(cx+8, control_y-12), (cx+8, control_y+12)], fill=icon_color, width=4)
                elif i == 3: # music note (dummy)
                    draw.ellipse((cx-6, control_y+2, cx-2, control_y+8), fill=icon_color)
                    draw.ellipse((cx+4, control_y, cx+8, control_y+6), fill=icon_color)
                    draw.line([(cx-4, control_y+5), (cx-4, control_y-8), (cx+6, control_y-10), (cx+6, control_y+3)], fill=icon_color, width=2)
                    draw.line([(cx-4, control_y-8), (cx+6, control_y-10)], fill=icon_color, width=3)

            # 5. Button
            btn_w = 300
            btn_h = 80
            btn_x = 850
            btn_y = 560
            draw.rounded_rectangle((btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), radius=40, fill=btn_color)
            draw.text((btn_x + 40, btn_y + 20), "▶ Playing Now", font=self.font_btn, fill=text_color)

            image = image.convert("RGB")
            image.save(output)
            
            try: os.remove(temp)
            except Exception: pass
            
            return output
        except Exception:
            return config.DEFAULT_THUMB
