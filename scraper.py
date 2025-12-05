from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import time

class AuchanScraper:
    """
    Scraper pour extraire les commandes depuis la plateforme Auchan
    Utilise Firefox + Selenium
    """
    
    def __init__(self, email, password, headless=True):
        """
        Initialise le scraper
        
        Args:
            email (str): Email de connexion
            password (str): Mot de passe
            headless (bool): Mode sans interface graphique
        """
        self.email = email
        self.password = password
        
        # Configuration Firefox
        options = Options()
        if headless:
            options.add_argument("--headless")
        
        # Options supplémentaires pour stabilité
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.set_preference("general.useragent.override", 
                             "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0")
        
        # Initialisation du driver
        self.driver = webdriver.Firefox(options=options)
        self.driver.set_window_size(1920, 1080)
        self.wait = WebDriverWait(self.driver, 30)  # Augmenté à 30 secondes
        
    def navigate_to_login(self):
        """ÉTAPE 1 : Navigation vers la page de connexion"""
        self.driver.get("https://auchan.atgpedi.net")
        time.sleep(3)  # Attente initiale augmentée
        
        # Attendre et cliquer sur le bouton SSO @GP
        try:
            # Essayer plusieurs sélecteurs possibles
            sso_button = None
            selectors = [
                "//a[contains(@href, 'base_sso_openid_connect_authentifier')]",
                "//button[contains(text(), 'identifier')]",
                "//a[contains(text(), 'identifier')]"
            ]
            
            for selector in selectors:
                try:
                    sso_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if sso_button:
                        break
                except:
                    continue
            
            if sso_button:
                sso_button.click()
                time.sleep(3)
        except Exception as e:
            print(f"Avertissement navigation SSO: {e}")
            # Peut-être déjà sur la page de login
            pass
    
    def login(self):
        """ÉTAPE 2 : Authentification avec les identifiants"""
        # Attendre la page de login @GP
        self.wait.until(EC.presence_of_element_located((By.NAME, "_username")))
        
        # Remplir le formulaire
        email_field = self.driver.find_element(By.NAME, "_username")
        password_field = self.driver.find_element(By.NAME, "_password")
        
        email_field.clear()
        email_field.send_keys(self.email)
        
        password_field.clear()
        password_field.send_keys(self.password)
        
        # Cliquer sur "Se connecter"
        submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Se connecter') or @type='submit']")
        submit_button.click()
        
        # Attendre la redirection vers Auchan
        time.sleep(3)
        self.wait.until(lambda driver: "auchan.atgpedi.net" in driver.current_url)
    
    def navigate_to_orders(self):
        """ÉTAPE 3 : Navigation vers la liste des commandes"""
        # Attendre que la page d'accueil charge
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Commandes')]")))
        
        # Cliquer sur le menu "Commandes"
        commandes_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Commandes')]")
        commandes_link.click()
        
        # Attendre que la page des commandes charge
        time.sleep(3)
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Liste des commandes')]")))
    
    def reset_filters(self):
        """ÉTAPE 5 : Réinitialiser tous les filtres"""
        try:
            # Chercher le bouton "effacer" ou l'icône de reset
            reset_button = self.driver.find_element(
                By.XPATH, 
                "//button[contains(@onclick, 'delete_tags') or contains(@title, 'supprimer le filtre')]"
            )
            reset_button.click()
            time.sleep(2)
        except:
            # Pas de filtres actifs ou bouton non trouvé
            pass
    
    def set_pagination(self, lines=100):
        """ÉTAPE 6 : Configurer le nombre de lignes par page"""
        try:
            # Trouver le dropdown de pagination
            pagination_select = Select(self.driver.find_element(By.XPATH, "//select[contains(@class, 'form-control') or @name='lines_per_page']"))
            pagination_select.select_by_value(str(lines))
            time.sleep(2)
        except Exception as e:
            print(f"Avertissement : Impossible de changer la pagination - {e}")
    
    def sort_by_creation_date(self):
        """ÉTAPE 7 : Trier par date de création (décroissant)"""
        try:
            # Cliquer sur la colonne "Création le"
            creation_header = self.driver.find_element(By.XPATH, "//th[contains(., 'Création')]")
            creation_header.click()
            time.sleep(2)
            
            # Vérifier si on a besoin de cliquer une 2ème fois pour ordre décroissant
            # (dépend si c'était déjà trié ou non)
            current_url = self.driver.current_url
            if "order_reverse=false" in current_url:
                creation_header.click()
                time.sleep(2)
        except Exception as e:
            print(f"Avertissement : Impossible de trier - {e}")
    
    def extract_orders(self, limit=20):
        """
        ÉTAPE 8 : Extraction des commandes du tableau
        
        Args:
            limit (int): Nombre maximum de commandes à extraire
            
        Returns:
            list: Liste de dictionnaires contenant les données des commandes
        """
        # Attendre que le tableau charge
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//tbody/tr")))
        time.sleep(1)
        
        # Extraire les lignes du tableau
        rows = self.driver.find_elements(By.XPATH, "//tbody/tr")[:limit]
        
        orders = []
        
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                # Ignorer les lignes vides ou de pagination
                if len(cells) < 8:
                    continue
                
                order = {
                    "numero": cells[0].text.strip(),
                    "client": cells[1].text.strip(),
                    "livrer_a": cells[2].text.strip(),
                    "creation_le": cells[3].text.strip(),
                    "livrer_le": cells[4].text.strip(),
                    "gln": cells[5].text.strip(),
                    "montant": cells[6].text.strip(),
                    "statut": cells[7].text.strip()
                }
                
                # Vérifier que la ligne contient des données valides
                if order["numero"] and order["numero"] != "":
                    orders.append(order)
                    
            except Exception as e:
                print(f"Erreur lors de l'extraction d'une ligne : {e}")
                continue
        
        return orders
    
    def close(self):
        """Ferme le navigateur"""
        try:
            self.driver.quit()
        except:
            pass

    def __del__(self):
        """Destructeur pour s'assurer que le navigateur se ferme"""
        self.close()
