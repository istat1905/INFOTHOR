import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import time

class AuchanScraper:
    """
    Scraper pour extraire les commandes du portail Auchan
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = "https://auchan.atgpedi.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def login(self) -> bool:
        """
        Effectue la connexion au portail
        Returns:
            bool: True si connexion réussie, False sinon
        """
        try:
            print("=" * 50)
            print("DEBUT CONNEXION")
            print("=" * 50)
            
            # Étape 1: Accéder à la page d'accueil
            print("\n1. Accès page d'accueil Auchan...")
            response = self.session.get(f"{self.base_url}/index.php")
            print(f"   Status: {response.status_code}")
            print(f"   URL: {response.url}")
            
            if response.status_code != 200:
                print(f"   ❌ Erreur: {response.status_code}")
                return False

            # Étape 2: Cliquer sur "M'identifier avec mon compte @GP"
            print("\n2. Redirection vers SSO @GP...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Chercher le lien SSO (visible dans l'image 1)
            sso_link = soup.find('a', {'class': 'btn btn-outline-red atgp btn-lg btn-block'})
            if sso_link:
                sso_url = sso_link.get('href', '')
                print(f"   Lien SSO trouvé: {sso_url[:50]}...")
            else:
                # Fallback sur l'URL SSO directe
                sso_url = f"{self.base_url}/call.php?call=base_sso_openid_connect_authentifier"
                print(f"   Utilisation URL SSO par défaut")
            
            response = self.session.get(sso_url, allow_redirects=True)
            print(f"   Status: {response.status_code}")
            print(f"   URL finale: {response.url}")
            
            if response.status_code != 200:
                print(f"   ❌ Erreur SSO: {response.status_code}")
                return False

            # Étape 3: On devrait être sur accounts.atgpedi.net/login
            print("\n3. Page de connexion @GP...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Chercher le formulaire (visible dans l'image 2)
            form = soup.find('form', {'class': 'form'})
            if not form:
                form = soup.find('form')
            
            if not form:
                print("   ❌ Formulaire non trouvé")
                print(f"   URL actuelle: {response.url}")
                return False
            
            print("   ✅ Formulaire de connexion trouvé")

            # Récupérer l'action du formulaire
            form_action = form.get('action', '')
            if not form_action:
                form_action = response.url
            elif not form_action.startswith('http'):
                base = 'https://accounts.atgpedi.net'
                form_action = f"{base}{form_action}"
            
            print(f"   Action: {form_action}")

            # Préparer les données de connexion
            login_data = {}
            
            # Récupérer tous les champs du formulaire
            for input_field in form.find_all('input'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                input_type = input_field.get('type', 'text')
                
                if name:
                    if input_type == 'hidden':
                        login_data[name] = value
                        print(f"   Champ caché: {name} = {value[:30]}...")
                    elif 'username' in name.lower() or 'email' in name.lower():
                        login_data[name] = self.username
                        print(f"   Champ username: {name}")
                    elif 'password' in name.lower():
                        login_data[name] = self.password
                        print(f"   Champ password: {name}")

            # Vérifier qu'on a bien les identifiants
            has_username = any('username' in k.lower() or 'email' in k.lower() for k in login_data.keys())
            has_password = any('password' in k.lower() for k in login_data.keys())
            
            if not has_username or not has_password:
                print("   ⚠️ Champs username/password non détectés, ajout manuel...")
                login_data['_username'] = self.username
                login_data['_password'] = self.password

            print(f"   Total champs formulaire: {len(login_data)}")

            # Étape 4: Soumettre le formulaire
            print("\n4. Soumission du formulaire...")
            response = self.session.post(
                form_action, 
                data=login_data, 
                allow_redirects=True,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://accounts.atgpedi.net',
                    'Referer': response.url
                }
            )
            print(f"   Status: {response.status_code}")
            print(f"   URL finale: {response.url}")
            
            if response.status_code != 200:
                print(f"   ❌ Erreur soumission: {response.status_code}")
                return False

            # Étape 5: Vérifier le succès
            print("\n5. Vérification connexion...")
            page_text = response.text.lower()
            
            # Vérifier qu'on est bien de retour sur auchan.atgpedi.net
            if 'auchan.atgpedi.net' in response.url:
                print("   ✅ Retour sur le portail Auchan")
            
            success_indicators = [
                'bonjour' in page_text,
                'commandes' in page_text,
                'logout' in page_text,
                'déconnexion' in page_text,
                'mon compte' in page_text
            ]
            
            failure_indicators = [
                'invalid' in page_text,
                'incorrect' in page_text,
                'erreur' in page_text,
                'error' in page_text
            ]
            
            success_count = sum(success_indicators)
            failure_count = sum(failure_indicators)
            
            print(f"   Indicateurs de succès: {success_count}/5")
            print(f"   Indicateurs d'échec: {failure_count}")
            
            if success_count >= 1 and failure_count == 0:
                print("\n✅ CONNEXION RÉUSSIE!")
                print("=" * 50)
                return True
            else:
                print("\n❌ CONNEXION ÉCHOUÉE")
                print(f"   Vérifiez vos identifiants")
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
        Returns:
            List[Dict]: Liste des commandes avec leurs détails
        """
        try:
            orders_url = f"{self.base_url}/gui.php?page=documents_commandes_liste"
            clear_filters_url = f"{self.base_url}/gui.php?query=documents_commandes_liste&page=documents_commandes_liste&acces_page=1&lines_per_page=50"
            self.session.get(clear_filters_url)
            time.sleep(1)
            response = self.session.get(orders_url + "&lines_per_page=1000")

            if response.status_code != 200:
                print(f"Erreur page commandes: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            tbody = soup.find('tbody')
            if not tbody:
                print("Tableau des commandes non trouvé")
                return []

            orders = []
            rows = tbody.find_all('tr')
            print(f"Lignes trouvées: {len(rows)}")

            for row in rows:
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
                    print(f"Erreur extraction ligne: {str(e)}")
                    continue

            print(f"Commandes extraites: {len(orders)}")
            return orders

        except Exception as e:
            print(f"Erreur extraction commandes: {str(e)}")
            return []

    def _extract_text(self, cell) -> str:
        if not cell:
            return ""
        text = cell.get_text(strip=True)
        return re.sub(r'\s+', ' ', text)

    def get_order_details(self, order_number: str) -> Optional[Dict]:
        try:
            detail_url = f"{self.base_url}/gui.php?page=documents_commandes_voir&numero={order_number}"
            response = self.session.get(detail_url)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            details = {'numero': order_number}
            return details

        except Exception as e:
            print(f"Erreur récupération détails: {str(e)}")
            return None

    def close(self):
        self.session.close()
