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
            
            # Background
            image = Image.new("RGBA", size, color="#123d4d")
            draw = ImageDraw.Draw(image)

            # 1. Album art
            album_size = (450, 450)
            try:
                album = Image.open(temp).convert("RGBA")
                album = ImageOps.fit(album, album_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            except Exception:
                album = Image.new("RGBA", album_size, color="#444444")
                
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

            # 3. Green checkmark
            check_center = (1120, 160)
            check_radius = 28
            draw.ellipse((check_center[0]-check_radius, check_center[1]-check_radius, 
                          check_center[0]+check_radius, check_center[1]+check_radius), fill="#2dd460")
            # Draw tick
            draw.line([(1105, 160), (1115, 172), (1135, 148)], fill="white", width=7, joint="curve")

            # 4. Controls
            control_y = 600
            control_x_start = 125
            spacing = 110
            radius = 38
            
            for i in range(4):
                cx = control_x_start + i * spacing
                fill_color = "#e0e0e0" if i == 2 else "#2a5969"
                draw.ellipse((cx-radius, control_y-radius, cx+radius, control_y+radius), fill=fill_color)
                
                # draw icons
                if i == 0: # prev
                    draw.polygon([(cx+8, control_y-12), (cx+8, control_y+12), (cx-8, control_y)], fill="#8bbcc9")
                    draw.line([(cx-8, control_y-12), (cx-8, control_y+12)], fill="#8bbcc9", width=4)
                elif i == 1: # play
                    draw.polygon([(cx-5, control_y-14), (cx-5, control_y+14), (cx+12, control_y)], fill="#8bbcc9")
                elif i == 2: # next
                    draw.polygon([(cx-8, control_y-12), (cx-8, control_y+12), (cx+8, control_y)], fill="#4a4a4a")
                    draw.line([(cx+8, control_y-12), (cx+8, control_y+12)], fill="#4a4a4a", width=4)
                elif i == 3: # music note (dummy)
                    draw.ellipse((cx-6, control_y+2, cx-2, control_y+8), fill="#8bbcc9")
                    draw.ellipse((cx+4, control_y, cx+8, control_y+6), fill="#8bbcc9")
                    draw.line([(cx-4, control_y+5), (cx-4, control_y-8), (cx+6, control_y-10), (cx+6, control_y+3)], fill="#8bbcc9", width=2)
                    draw.line([(cx-4, control_y-8), (cx+6, control_y-10)], fill="#8bbcc9", width=3)

            # 5. Button
            btn_w = 300
            btn_h = 80
            btn_x = 850
            btn_y = 560
            draw.rounded_rectangle((btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), radius=40, fill="#04f4d2")
            draw.text((btn_x + 35, btn_y + 20), "+ Creativestyle", font=self.font_btn, fill="#104a52")

            image = image.convert("RGB")
            image.save(output)
            
            try: os.remove(temp)
            except Exception: pass
            
            return output
        except Exception:
            return config.DEFAULT_THUMB
