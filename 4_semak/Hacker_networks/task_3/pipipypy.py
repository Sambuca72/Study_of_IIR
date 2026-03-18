import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By


driver = webdriver.Chrome()
try:
    driver.get("https://quotes.toscrape.com/login")
    driver.find_element(By.ID, "username").send_keys("Hacker777")
    driver.find_element(By.ID, "password").send_keys("LevLox")
    
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    time.sleep(2)
    
    with open("result.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Текст цитаты", "Автор", "Теги", "Ссылка на автора"])
        writer.writerow([])
        
        while True:
            quotes = driver.find_elements(By.CLASS_NAME, "quote")
            
            for quote in quotes:
                text = quote.find_element(By.CLASS_NAME, "text").text
                author = quote.find_element(By.CLASS_NAME, "author").text
                
                tags_elements = quote.find_elements(By.CLASS_NAME, "tag")
                tags = ", ".join([tag.text for tag in tags_elements])
                
                author_link = quote.find_element(By.TAG_NAME, "a").get_attribute("href")
                
                writer.writerow([text, author, tags, author_link])
                writer.writerow([])
                
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "li.next > a")
                next_button.click()
                time.sleep(2)
            except:
                print("Парсинг окончен")
                break       
finally:
    driver.quit()
