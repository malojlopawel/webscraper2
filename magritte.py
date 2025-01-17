import time
import requests
import os
import json
import re
from playwright.async_api import async_playwright

class MagritteScraper:
  def __init__(self,
               url="https://fine-arts-museum.be/fr/la-collection/artist/magritte-rena?string=magritte&page=1",
               base_url="https://fine-arts-museum.be"):
      self.hrefs = []
      self.base_url = base_url
      self.url = url
      self.data = []
      self.pages = 8

  async def scrape(self):
      async with async_playwright() as p:
          self.browser = await p.chromium.launch(headless=False)
          self.context = await self.browser.new_context()
          self.page = await self.context.new_page()
          await self.go_to(self.url)
          await self.skip_cookies()
          await self.get_hrefs()
          time.sleep(15)
          self.page.set_default_timeout(10000)
          await self.get_data()
          self.save_data()
          await self.browser.close()


  async def skip_cookies(self):
      element = await self.find_el('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll')
      await element.click()


  async def find_el(self, selector: str):
      await self.wait_for_el(selector)
      return await self.page.query_selector(selector)


  async def find_els(self, selector: str):
      await self.wait_for_el(selector)
      return await self.page.query_selector_all(selector)


  async def wait_for_el(self, selector: str):
      await self.page.wait_for_selector(selector)


  async def go_to(self, url, tabs=False):
      hack = True
      while hack:
          try:
              await self.page.goto(url, timeout=60000)
              hack = False
          except Exception as e:
              print(e)
              print(f'error go to {url}')




  async def get_hrefs(self):
    for i in range(self.pages):
        if i > 0:
            pagination = await self.find_el(
                '.pagination ul > li:last-child > a')
            await pagination.click()
        print(f"{i}\n\n\n")
        el = await self.find_els(
            '.artworks li > a')
        for e in el:
            self.hrefs.append(await e.get_attribute('href'))
    print(self.hrefs)
        

  async def get_image(self, href):
    image = None
    i = 0
    while not image and i < 30:
        try:
            image_element = await self.find_el(".image > img")
            if image_element:
                image = await image_element.get_attribute('src')
        except Exception as e:
            print(f"Error: {e}\n\nOn page: {href}")
            return None
        time.sleep(0.5)
        i += 1
    if image and image.startswith("/"):
        image = f"{self.base_url}{image}"
    return image


  def curl_image(self, image, id):
    try:
        os.mkdir("images")
    except FileExistsError:
        pass
    if image != "null":
        image_response = requests.get(image)
        if image_response.status_code == 200:
            with open(f'images/{id}.jpg', 'wb') as img_file:
                img_file.write(image_response.content)


  async def get_title(self):
    title_element = await self.find_el(".span8 h2")
    full_text = await title_element.inner_text()
    if '"' in full_text:
        title = full_text.split('"')[1]  
    else:
        title = full_text.strip() 
    return title


  import re

  async def get_info(self):
    list_items = await self.find_els(".artwork-description ul li")
    li_texts = [await li.inner_text() for li in list_items]
    
    info = {
        "technique": li_texts[0] if len(li_texts) > 0 else None,
        "signature": li_texts[1] if len(li_texts) > 1 else None,
        "dimensions": li_texts[2] if len(li_texts) > 2 else None,
        "origin": li_texts[3] if len(li_texts) > 3 else None
    }

    date_element = await self.find_el(".span8 .inv")
    if date_element:
        full_date_text = (await date_element.inner_text()).strip()
        match = re.search(r"\((.*?)\)", full_date_text)  
        info["date"] = match.group(1) if match else None
    else:
        info["date"] = None

    return info


  def save_data(self):
      try:
          os.mkdir("dist")
      except FileExistsError:
          pass
      open("dist/data.json", "w", encoding="utf8").write(
          json.dumps([d for d in self.data], indent=4, ensure_ascii=False))


  async def get_data(self):
      for index, href in enumerate(self.hrefs):
          print(f"Processing artwork {index + 1}/{len(self.hrefs)}: {href}")
          await self.go_to(f"{self.base_url}{href}")
          image = await self.get_image(href)
          if not image:
              continue
          title = await self.get_title()
          get_info = await self.get_info()

          self.curl_image(image, index)
          self.data.append({
              "id": index,
              "title": title,
              "date": get_info["date"],
              "name_of_artist": "René Magritte",
              "technique": get_info["technique"],
              "dimensions": get_info["dimensions"],
              "signature": get_info["signature"],
              "origin": get_info["origin"],
              "image": image,
          })


if __name__ == "__main__":
   import asyncio
   scraper = MagritteScraper()
   asyncio.run(scraper.scrape())

