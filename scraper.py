from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import time

class AuchanScraper:
    """
    Scraper pour extraire les commandes du portail Auchan avec Playwright
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = "https://auchan.atgpedi.net"
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    def _init_browser(self):
        """Initialise le navigateur Playwright"""
        print("🔧 Initialisation du navigateur...")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
            ]
        )
        
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
        
        print("✅ Navigateur initialisé")

    def login(self) -> bool:
        """
        Effectue la connexion au portail
        Returns:
            bool: True si connexion réussie, False sinon
        """
        try:
            print("\n" + "=" * 50)
            print("DEBUT CONNEXION")
            print("=" * 50)
            
            if not self.page:
                self._init_browser()
            
            # Étape 1: Accéder à la page d'accueil
            print("\n1. Accès page d'accueil...")
            self.page.goto(f"{self.base_url}/index.php", wait_until="domcontentloaded")
            time.sleep(2)
            print(f"   ✅ Page chargée")
            
            # Étape 2: Cliquer sur le bouton SSO
            print("\n2. Clic sur le bouton SSO...")
            try:
                # Chercher le bouton SSO
                sso_button = self.page.locator('a.btn.btn-outline-red.atgp, a[href*="sso"]').first
                sso_button.click()
                time.sleep(3)
                print(f"   ✅ Redirection SSO")
            except:
                print(f"   ⚠️ Tentative URL directe...")
                self.page.goto(f"{self.base_url}/call.php?call=base_sso_openid_connect_authentifier")
                time.sleep(3)
            
            # Étape 3: Remplir le formulaire
            print("\n3. Remplissage formulaire...")
            
            # Attendre le champ username
            self.page.wait_for_selector('input[name="_username"]', timeout=10000)
            
            # Remplir email
            self.page.fill('input[name="_username"]', self.username)
            print(f"   ✅ Email: {self.username}")
            
            # Remplir mot de passe
            self.page.fill('input[name="_password"]', self.password)
            print(f"   ✅ Mot de passe saisi")
            
            time.sleep(1)
            
            # Étape 4: Soumettre
            print("\n4. Soumission...")
            self.page.click('button[type="submit"]')
            
            # Attendre la redirection
            time.sleep(5)
            
            # Étape 5: Vérification
            print("\n5. Vérification...")
            
            current_url = self.page.url
            if 'auchan.atgpedi.net' in current_url:
                page_content = self.page.content().lower()
                
                success_indicators = [
                    'bonjour' in page_content,
                    'commandes' in page_content,
                    'déconnexion' in page_content or 'logout' in page_content
                ]
                
                if any(success_indicators):
                    print("\n✅ CONNEXION RÉUSSIE!")
                    print("=" * 50)
                    return True
            
            print("\n❌ CONNEXION ÉCHOUÉE")
            print(f"   URL actuelle: {current_url}")
            print("=" * 50)
            return False
            
        except Exception as e:
            print(f"\n❌ EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def extract_orders(self) -> List[Dict]:
        """
        Extrait la liste des commandes
        """
        try:
            print("\n" + "=" * 50)
            print("EXTRACTION DES COMMANDES")
            print("=" * 50)
            
            orders_url = f"{self.base_url}/gui.php?query=documents_commandes_liste&page=documents_commandes_liste&acces_page=1&lines_per_page=1000"
            
            print("\n1. Navigation vers liste commandes...")
            self.page.goto(orders_url, wait_until="domcontentloaded")
            time.sleep(3)
            
            print("\n2. Attente chargement tableau...")
            self.page.wait_for_selector('tbody', timeout=10000)
            
            print("\n3. Extraction données...")
            html_content = self.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            tbody = soup.find('tbody')
            if not tbody:
                print("   ❌ Tableau non trouvé")
                return []
            
            orders = []
            rows = tbody.find_all('tr')
            print(f"   Lignes trouvées: {len(rows)}")
            
            for idx, row in enumerate(rows, 1):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 8:
                        continue
                    
                    order = {
                        'numero': self._extract_text(cells[1]),
                        'client': self._extract_text(cells[2]),
                        'livrer_a': self._extract_text(cells[3]),
                        'creation_le': self._extract_text(cells[4]),
                        'livrer_le': self._extract_text(cells[5]),
                        'gln_commande_par': self._extract_text(cells[6]),
                        'montant_calcule': self._extract_text(cells[7]),
                        'statut': self._extract_text(cells[8]) if len(cells) > 8 else '',
                    }
                    
                    if order['numero'] and len(order['numero']) > 3:
                        orders.append(order)
                        
                except Exception as e:
                    print(f"   ⚠️ Erreur ligne {idx}: {str(e)}")
                    continue
            
            print(f"\n✅ {len(orders)} commandes extraites!")
            print("=" * 50)
            return orders
            
        except Exception as e:
            print(f"\n❌ Erreur extraction: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_text(self, cell) -> str:
        """Extrait et nettoie le texte d'une cellule"""
        if not cell:
            return ""
        text = cell.get_text(strip=True)
        return re.sub(r'\s+', ' ', text)

    def get_order_details(self, order_number: str) -> Optional[Dict]:
        """
        Récupère les détails d'une commande spécifique
        """
        try:
            detail_url = f"{self.base_url}/gui.php?page=documents_commandes_voir&numero={order_number}"
            self.page.goto(detail_url, wait_until="domcontentloaded")
            time.sleep(2)
            
            html_content = self.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            details = {'numero': order_number}
            
            return details
            
        except Exception as e:
            print(f"Erreur détails: {str(e)}")
            return None

    def close(self):
        """Ferme le navigateur"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("\n🔒 Navigateur fermé")
        except Exception as e:
            print(f"Erreur fermeture: {e}")
