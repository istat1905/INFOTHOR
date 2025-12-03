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
        # ✅ Renommé pour éviter le conflit avec la méthode login()
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
            # Étape 1: Accéder à la page d'accueil
            response = self.session.get(f"{self.base_url}/index.php")
            if response.status_code != 200:
                print(f"Erreur page d'accueil: {response.status_code}")
                return False

            # Étape 2: Auth SSO
            auth_url = f"{self.base_url}/call.php?call=base_sso_openid_connect_authentifier"
            response = self.session.get(auth_url, allow_redirects=True)
            if response.status_code != 200:
                print(f"Erreur SSO: {response.status_code}")
                return False

            # Étape 3: Récupérer le formulaire de connexion
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            if not form:
                print("Formulaire de connexion non trouvé")
                return False

            form_action = form.get('action', '')
            if not form_action.startswith('http'):
                form_action = f"https://www.atgp.net{form_action}"

            # Préparer les données
            login_data = {
                'username': self.username,
                'password': self.password
            }

            # Ajouter les champs cachés
            for input_field in form.find_all('input', type='hidden'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                if name:
                    login_data[name] = value

            # Soumettre le formulaire
            response = self.session.post(form_action, data=login_data, allow_redirects=True)
            if response.status_code != 200:
                print(f"Erreur soumission formulaire: {response.status_code}")
                return False

            # Vérifier succès
            if "Bonjour" in response.text or "Commandes" in response.text:
                print("Connexion réussie !")
                return True
            else:
                print("Connexion échouée - identifiants incorrects ou page modifiée")
                return False

        except Exception as e:
            print(f"Erreur lors de la connexion: {str(e)}")
            return False

    def extract_orders(self) -> List[Dict]:
        """
        Extrait la liste des commandes
        Returns:
            List[Dict]: Liste des commandes avec leurs détails
        """
        try:
            orders_url = f"{self.base_url}/gui.php?page=documents_commandes_liste"
            clear_filters_url = f"{self.base_url}/gui.php?query=documents_commandes_liste&page=documents_commandes_liste&acces_page=1&lines_per_page=100"
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
            details = {'numero': order_number}  # Ajouter d'autres champs si nécessaire
            return details

        except Exception as e:
            print(f"Erreur récupération détails: {str(e)}")
            return None

    def close(self):
        self.session.close()


# Exemple d'utilisation avec Streamlit secrets
if __name__ == "__main__":
    import streamlit as st

    username = st.secrets["username"]
    password = st.secrets["password"]

    scraper = AuchanScraper(username, password)

    print("Tentative de connexion...")
    if scraper.login():
        print("Connexion réussie !")
        orders = scraper.extract_orders()
        print(f"\nNombre de commandes: {len(orders)}")
        if orders:
            print("\nPremière commande:")
            for key, value in orders[0].items():
                print(f"  {key}: {value}")
    else:
        print("Échec de la connexion")

    scraper.close()
