import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from database import get_connection


def parse_quotes(url: str) -> dict:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    parsed_data = []
    
    try:
        print(f"Opening: {url}")
        driver.get(url)
        time.sleep(2)
                
        page = 1
        while True:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "quote"))) # Ждём загрузки цитат

            quotes = driver.find_elements(By.CLASS_NAME, "quote")
            
            for quote in quotes:
                try:
                    text = quote.find_element(By.CLASS_NAME, "text").text
                    author = quote.find_element(By.CLASS_NAME, "author").text
                    tags_elem = quote.find_elements(By.CLASS_NAME, "tag")
                    tags = ", ".join([tag.text for tag in tags_elem])
                    author_elem = quote.find_element(By.CSS_SELECTOR, ".author + a")
                    author_link = author_elem.get_attribute("href")
                    
                    parsed_data.append({"text": text, "author": author, "tags": tags, "author_link": author_link})
                except Exception as e:
                    print(f"Error parsing quote: {e}")
                    continue
            
            # Переход на следующую страницу
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "li.next > a")
                if next_btn.is_enabled():
                    next_btn.click()
                    time.sleep(1)
                    page += 1
                else:
                    break
            except:
                break
        
        if parsed_data:
            save_to_db(parsed_data)
            print(f"Сохранено {len(parsed_data)} цитат в БД")
            return {"status": "success", "count": len(parsed_data)}
        else:
            return {"status": "error", "message": "No data parsed"}
    
    except Exception as e:
        print(f"Ошибка парснга:( : {e}")
        return {"status": "error", "message": str(e)}
    finally:
        driver.quit()

def save_to_db(data: list) -> None:
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        for item in data:
            cur.execute("""
                INSERT INTO quotes (text, author, tags, author_link)
                VALUES (%s, %s, %s, %s)""",
                (item["text"], item["author"], item["tags"], item["author_link"]))
        conn.commit()
        print("Данные сохранены в PostgresSQL")
    
    except Exception as e:
        conn.rollback()
        print(f"Ошибка БД: {e}")
        raise
    
    finally:
        cur.close()
        conn.close()