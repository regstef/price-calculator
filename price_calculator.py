import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
import json
import csv
import os
import io
import shutil
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
import time
import logging
from typing import Dict, List, Tuple, Optional, Any

# Konstanten
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://qormgjgpisbzyegipbiq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFvcm1namdwaXNienllZ2lwYmlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjkxODY2NjMsImV4cCI6MjA0NDc2MjY2M30.JB7xuS8R8nBShuTYm5LmZifHR7SpsEYxcVOaag8uRKI")
DEFAULT_HOURLY_RATE = 30.0
DEFAULT_FIXED_COSTS = 606.0
DEFAULT_OUTFITS_PER_MONTH = 3
DEFAULT_CONSULTATION_HOURS = 2.0
DEFAULT_PROFIT_MARGIN = 20
ALL_POSSIBLE_COMPONENTS = ['Kleid', 'Jacke', 'Oberteil', 'Hose', 'Rock', 'Overall']

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Typen
OutfitData = Dict[str, Any]
ComponentCosts = Dict[str, Dict[str, Dict[str, float]]]

class SupabaseManager:
    """Klasse zur Verwaltung der Supabase-Verbindung und -Operationen."""

    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    @st.cache_data(ttl=3600)
    def load_cached_data(_self, table_name: str) -> pd.DataFrame:
        """
        Lädt Daten aus einer Supabase-Tabelle mit Caching.
        
        Args:
            table_name (str): Name der Tabelle.
        
        Returns:
            pd.DataFrame: Geladene Daten als DataFrame.
        """
        try:
            response = _self.client.table(table_name).select("*").execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten aus {table_name}: {e}")
            st.error(f"Fehler beim Laden der Daten aus {table_name}: {e}")
            return pd.DataFrame()

    def load_data(self, table_name: str) -> pd.DataFrame:
        """
        Lädt Daten aus einer Supabase-Tabelle ohne Caching.
        
        Args:
            table_name (str): Name der Tabelle.
        
        Returns:
            pd.DataFrame: Geladene Daten als DataFrame.
        """
        try:
            response = self.client.table(table_name).select("*").execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten aus {table_name}: {e}")
            st.error(f"Fehler beim Laden der Daten aus {table_name}: {e}")
            return pd.DataFrame()

    def update_data(self, data: pd.DataFrame, table_name: str) -> bool:
        """
        Aktualisiert Daten in einer Supabase-Tabelle.
        
        Args:
            data (pd.DataFrame): Zu aktualisierende Daten.
            table_name (str): Name der Tabelle.
        
        Returns:
            bool: True, wenn erfolgreich, sonst False.
        """
        try:
            self.client.table(table_name).upsert(data.to_dict(orient='records')).execute()
            return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Daten in {table_name}: {e}")
            st.error(f"Fehler beim Aktualisieren der Daten in {table_name}: {e}")
            return False

    def save_outfit(self, outfit_data: OutfitData) -> None:
        """
        Speichert ein Outfit in der Datenbank.
        
        Args:
            outfit_data (OutfitData): Zu speichernde Outfit-Daten.
        """
        try:
            self.client.table('saved_outfits').insert(outfit_data).execute()
            st.success(f"Outfit '{outfit_data['name']}' erfolgreich gespeichert!")
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Outfits: {e}")
            st.error(f"Fehler beim Speichern des Outfits: {e}")

    def delete_outfit(self, outfit_id: int) -> None:
        """
        Löscht ein Outfit aus der Datenbank.
        
        Args:
            outfit_id (int): ID des zu löschenden Outfits.
        """
        try:
            self.client.table('saved_outfits').delete().eq('id', outfit_id).execute()
            st.success(f"Outfit mit ID {outfit_id} erfolgreich gelöscht!")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Outfits: {e}")
            st.error(f"Fehler beim Löschen des Outfits: {e}")

    def delete_material(self, material_name: str) -> None:
        """
        Löscht ein Material aus der Datenbank.
        
        Args:
            material_name (str): Name des zu löschenden Materials.
        """
        try:
            self.client.table('materials').delete().eq('material', material_name).execute()
            st.success(f"Material '{material_name}' erfolgreich gelöscht!")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Materials: {e}")
            st.error(f"Fehler beim Löschen des Materials: {e}")

    def delete_accessory(self, accessory_name: str) -> None:
        """
        Löscht ein Zubehör aus der Datenbank.
        
        Args:
            accessory_name (str): Name des zu löschenden Zubehörs.
        """
        try:
            self.client.table('accessories').delete().eq('accessory', accessory_name).execute()
            st.success(f"Zubehör '{accessory_name}' erfolgreich gelöscht!")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Zubehörs: {e}")
            st.error(f"Fehler beim Löschen des Zubehörs: {e}")

class UIManager:
    """Klasse zur Verwaltung der Benutzeroberfläche."""

    @staticmethod
    def display_sidebar() -> Tuple[float, float, int, float, float]:
        """
        Zeigt die Sidebar an und gibt die eingegebenen Werte zurück.
        
        Returns:
            Tuple[float, float, int, float, float]: Stundensatz, Fixkosten, Outfits pro Monat, Beratungsstunden, Gewinnmarge
        """
        with st.sidebar:
            st.header("Einstellungen")
            hourly_rate = st.number_input('Stundensatz (€)', min_value=0.0, value=DEFAULT_HOURLY_RATE, step=0.5, 
                                          help="Der Stundensatz für die Arbeitszeit.")
            fixed_costs = st.number_input('Fixkosten (€)', min_value=0.0, value=DEFAULT_FIXED_COSTS, step=10.0, 
                                          help="Monatliche Fixkosten des Unternehmens.")
            outfits_per_month = st.number_input('Outfits pro Monat', min_value=1, value=DEFAULT_OUTFITS_PER_MONTH, step=1, 
                                                help="Geschätzte Anzahl der produzierten Outfits pro Monat.")
            consultation_hours = st.number_input('Beratungsstunden', min_value=0.0, value=DEFAULT_CONSULTATION_HOURS, step=0.5, 
                                                 help="Durchschnittliche Beratungszeit pro Outfit.")
            profit_margin = st.slider('Gewinnmarge (%)', min_value=0, max_value=100, value=DEFAULT_PROFIT_MARGIN, step=5, 
                                      help="Gewünschte Gewinnmarge in Prozent.")
        
        return hourly_rate, fixed_costs, outfits_per_month, consultation_hours, profit_margin

    @staticmethod
    def display_cost_overview(cost_data: List[Dict[str, Any]]) -> None:
        """
        Zeigt eine Kostenübersicht an.
        
        Args:
            cost_data (List[Dict[str, Any]]): Liste der Kostendaten.
        """
        df = pd.DataFrame(cost_data)
        st.table(df)

    @staticmethod
    def create_pie_chart(costs: List[float], labels: List[str]) -> None:
        """
        Erstellt ein Kuchendiagramm der Kosten.
        
        Args:
            costs (List[float]): Liste der Kostenwerte.
            labels (List[str]): Liste der Kostenbeschriftungen.
        """
        positive_costs = [cost for cost in costs if cost > 0]
        positive_labels = [label for cost, label in zip(costs, labels) if cost > 0]
        
        if not positive_costs:
            st.warning("Keine positiven Kosten vorhanden. Kuchendiagramm kann nicht erstellt werden.")
            return
        
        fig, ax = plt.subplots()
        try:
            wedges, texts, autotexts = ax.pie(positive_costs, 
                                            labels=positive_labels, 
                                            autopct=lambda pct: f'{pct:.1f}%' if pct > 5 else '',
                                            startangle=90,
                                            pctdistance=0.85)
            
            ax.legend(wedges, positive_labels,
                    title="Kostenarten",
                    loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1))
            
            plt.setp(autotexts, size=8, weight="bold")
            ax.set_title("Kostenverteilung")
            
            st.pyplot(fig)
        except Exception as e:
            logger.error(f"Fehler bei der Erstellung des Kuchendiagramms: {e}")
            st.error(f"Fehler bei der Erstellung des Kuchendiagramms: {e}")
            st.write("Kostendaten:", positive_costs)
            st.write("Labels:", positive_labels)

class OutfitCalculator:
    """Klasse zur Berechnung der Outfit-Kosten."""

    @staticmethod
    def calculate_costs(components: List[str], component_costs: ComponentCosts, materials_db: pd.DataFrame, 
                        accessories_db: pd.DataFrame, hourly_rate: float, overhead_costs: float, 
                        consultation_costs: float, profit_margin: float) -> Tuple[List[Dict[str, Any]], float, float, float, float, float, float]:
        """
        Berechnet die Kosten für ein Outfit.
        
        Args:
            components (List[str]): Liste der Outfit-Komponenten.
            component_costs (ComponentCosts): Kosten für jede Komponente.
            materials_db (pd.DataFrame): Materialdatenbank.
            accessories_db (pd.DataFrame): Zubehördatenbank.
            hourly_rate (float): Stundensatz.
            overhead_costs (float): Gemeinkosten.
            consultation_costs (float): Beratungskosten.
            profit_margin (float): Gewinnmarge in Prozent.
        
        Returns:
            Tuple[List[Dict[str, Any]], float, float, float, float, float, float]: 
            Kostendaten, Gesamtmaterialkosten, Gesamtzubehörkosten, Gesamtarbeitskosten, Gesamtkosten, Gewinnbetrag, Endpreis
        """
        if not components:
            st.warning("Keine Komponenten ausgewählt. Bitte wählen Sie mindestens eine Komponente aus.")
            return [], 0, 0, 0, 0, 0, 0

        cost_data = []
        total_material_cost = 0
        total_accessory_cost = 0
        total_labor_cost = 0

        for component in components:
            # Materialkosten berechnen
            for material, data in component_costs[component]['Materialien'].items():
                amount = data.get('amount', 0)
                cost = data.get('cost', 0)
                if cost == 0:
                    material_data = materials_db[materials_db['material'] == material]
                    if material_data.empty:
                        st.warning(f"Material '{material}' nicht in der Datenbank gefunden. Bitte überprüfen Sie die Materialien.")
                        continue
                    material_price = float(material_data['average_price'].iloc[0])
                    material_waste = float(material_data['waste_percentage'].iloc[0]) / 100
                    cost = amount * material_price * (1 + material_waste)
                
                total_material_cost += cost
                cost_data.append({
                    'Kategorie': 'Materialkosten',
                    'Komponente': component,
                    'Beschreibung': f"{material}: {amount} m",
                    'Betrag (€)': f"{cost:.2f}"
                })

            # Zubehörkosten berechnen
            for accessory, data in component_costs[component]['Zubehör'].items():
                amount = data.get('amount', 0)
                cost = data.get('cost', 0)
                if cost == 0:
                    accessory_data = accessories_db[accessories_db['accessory'] == accessory]
                    if accessory_data.empty:
                        st.warning(f"Zubehör '{accessory}' nicht in der Datenbank gefunden. Bitte überprüfen Sie das Zubehör.")
                        continue
                    accessory_price = float(accessory_data['price'].iloc[0])
                    cost = amount * accessory_price
                
                total_accessory_cost += cost
                cost_data.append({
                    'Kategorie': 'Zubehörkosten',
                    'Komponente': component,
                    'Beschreibung': f"{accessory}: {amount} Stück",
                    'Betrag (€)': f"{cost:.2f}"
                })

            # Arbeitskosten berechnen
            work_hours = component_costs[component]['Arbeitskosten'] / hourly_rate if isinstance(component_costs[component]['Arbeitskosten'], (int, float)) else 0
            labor_cost = work_hours * hourly_rate
            total_labor_cost += labor_cost
            cost_data.append({
                'Kategorie': 'Arbeitskosten',
                'Komponente': component,
                'Beschreibung': f"{work_hours:.2f} Stunden",
                'Betrag (€)': f"{labor_cost:.2f}"
            })

        # Gesamtkosten berechnen
        total_cost = total_material_cost + total_accessory_cost + total_labor_cost + overhead_costs + consultation_costs
        profit_amount = total_cost * (profit_margin / 100)
        final_price = total_cost + profit_amount

        # Gesamtübersicht hinzufügen
        cost_data.extend([
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Gesamtmaterialkosten', 'Betrag (€)': f"{total_material_cost:.2f}"},
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Gesamtzubehörkosten', 'Betrag (€)': f"{total_accessory_cost:.2f}"},
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Gesamtarbeitskosten', 'Betrag (€)': f"{total_labor_cost:.2f}"},
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Gemeinkosten', 'Betrag (€)': f"{overhead_costs:.2f}"},
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Beratungskosten', 'Betrag (€)': f"{consultation_costs:.2f}"},
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Gesamtproduktionskosten', 'Betrag (€)': f"{total_cost:.2f}"},
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': f'Gewinnbetrag ({profit_margin}%)', 'Betrag (€)': f"{profit_amount:.2f}"},
            {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Empfohlener Verkaufspreis', 'Betrag (€)': f"{final_price:.2f}"}
        ])

        return cost_data, total_material_cost, total_accessory_cost, total_labor_cost, total_cost, profit_amount, final_price

def sanitize_input(input_string: str) -> str:
    """
    Bereinigt eine Eingabezeichenfolge von nicht-alphanumerischen Zeichen.
    
    Args:
        input_string (str): Die zu bereinigende Zeichenfolge.
    
    Returns:
        str: Die bereinigte Zeichenfolge.
    """
    return ''.join(char for char in input_string if char.isalnum() or char.isspace())

def add_material(supabase_manager: SupabaseManager, material_name: str, average_price: float, waste_percentage: float) -> None:
    """
    Fügt ein neues Material zur Datenbank hinzu.
    
    Args:
        supabase_manager (SupabaseManager): Der Supabase-Manager.
        material_name (str): Name des Materials.
        average_price (float): Durchschnittspreis des Materials.
        waste_percentage (float): Abfallprozentsatz des Materials.
    """
    try:
        supabase_manager.client.table('materials').insert({
            'material': sanitize_input(material_name),
            'average_price': average_price,
            'waste_percentage': waste_percentage
        }).execute()
        st.success(f"Material '{material_name}' erfolgreich hinzugefügt!")
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Materials: {e}")
        st.error(f"Fehler beim Hinzufügen des Materials: {e}")

def add_accessory(supabase_manager: SupabaseManager, accessory_name: str, price: float) -> None:
    """
    Fügt ein neues Zubehör zur Datenbank hinzu.
    
    Args:
        supabase_manager (SupabaseManager): Der Supabase-Manager.
        accessory_name (str): Name des Zubehörs.
        price (float): Preis des Zubehörs.
    """
    try:
        supabase_manager.client.table('accessories').insert({
            'accessory': sanitize_input(accessory_name),
            'price': price
        }).execute()
        st.success(f"Zubehör '{accessory_name}' erfolgreich hinzugefügt!")
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Zubehörs: {e}")
        st.error(f"Fehler beim Hinzufügen des Zubehörs: {e}")

def display_saved_outfits(supabase_manager: SupabaseManager, ui_manager: UIManager, current_hourly_rate: float, current_overhead_costs: float, current_materials_db: pd.DataFrame, current_accessories_db: pd.DataFrame, current_profit_margin: float, consultation_hours: float = 2.0) -> None:
    """
    Zeigt die gespeicherten Outfits an und ermöglicht deren Verwaltung.
    """
    saved_outfits = supabase_manager.load_data('saved_outfits')
    
    if saved_outfits.empty:
        st.write("Keine Outfits gespeichert.")
    else:
        search_term = st.text_input("Suche nach Outfit-Namen")
        category_filter = st.multiselect("Nach Kategorie filtern", options=['Basics', 'Made-to-Order'])
        
        filtered_outfits = saved_outfits
        if search_term:
            filtered_outfits = filtered_outfits[filtered_outfits['name'].str.contains(search_term, case=False)]
        if category_filter:
            filtered_outfits = filtered_outfits[filtered_outfits['category'].isin(category_filter)]
        
        st.table(filtered_outfits[['name', 'category', 'final_price']])
        
        selected_outfit = st.selectbox("Outfit-Details anzeigen", options=filtered_outfits['name'])
        if selected_outfit:
            outfit = filtered_outfits[filtered_outfits['name'] == selected_outfit].iloc[0]
            with st.expander(f"Details für {selected_outfit}", expanded=True):
                display_outfit_details(supabase_manager, outfit, current_hourly_rate, current_overhead_costs, current_materials_db, current_accessories_db, current_profit_margin, consultation_hours)
            
            if st.button(f"Outfit '{selected_outfit}' bearbeiten"):
                st.session_state.editing_outfit = outfit
                st.rerun()

        if 'editing_outfit' in st.session_state:
            edit_outfit(supabase_manager, st.session_state.editing_outfit, current_materials_db, current_accessories_db, 
                        current_hourly_rate, current_overhead_costs, current_profit_margin, consultation_hours)

        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button('Alle Outfits aktualisieren'):
                with st.spinner('Outfits werden aktualisiert...'):
                    update_all_outfits(saved_outfits, current_hourly_rate, current_overhead_costs, current_profit_margin, consultation_hours)
                st.success("Alle Outfits wurden erfolgreich aktualisiert.")
                saved_outfits = supabase_manager.load_data('saved_outfits')
                st.rerun()
        with col2:
            if st.button('CSV erstellen'):
                generate_csv_download(saved_outfits)

def display_outfit_details(supabase_manager: SupabaseManager, outfit: pd.Series, current_hourly_rate: float, current_overhead_costs: float, current_materials_db: pd.DataFrame, current_accessories_db: pd.DataFrame, current_profit_margin: float, consultation_hours: float) -> None:
    """
    Zeigt die Details eines Outfits in einer einheitlichen, übersichtlichen Tabelle an.
    """
    try:
        components = json.loads(outfit['components'])
        materials = json.loads(outfit['materials'])
        accessories = json.loads(outfit['accessories'])
        work_hours = json.loads(outfit['work_hours'])
        
        # Erstellen einer Liste für die Tabellendaten
        table_data = []
        
        # Allgemeine Informationen
        table_data.append({"Beschreibung": "Kategorie", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": outfit['category']})
        table_data.append({"Beschreibung": "Gemeinkosten", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": f"{current_overhead_costs:.2f} €"})
        table_data.append({"Beschreibung": "Beratungsstunden", "Menge": f"{consultation_hours:.2f}", "Einzelpreis": f"{current_hourly_rate:.2f} €", "Gesamtpreis": f"{consultation_hours * current_hourly_rate:.2f} €"})
        
        total_material_cost = 0
        total_accessory_cost = 0
        total_labor_cost = 0
        
        # Komponenten, Materialien, Zubehör und Arbeitsstunden
        for component in components:
            table_data.append({"Beschreibung": f"Komponente: {component}", "Menge": "---", "Einzelpreis": "---", "Gesamtpreis": "---"})
            
            component_total_cost = 0
            
            # Materialien
            for material, data in materials.get(component, {}).items():
                material_data = current_materials_db[current_materials_db['material'] == material].iloc[0]
                material_price = float(material_data['average_price'])
                material_waste = float(material_data['waste_percentage']) / 100
                material_cost = data['cost']
                total_material_cost += material_cost
                component_total_cost += material_cost
                table_data.append({
                    "Beschreibung": f"Material: {material}",
                    "Menge": f"{data['amount']:.2f} m",
                    "Einzelpreis": f"{material_price:.2f} € (inkl. {material_waste*100:.1f}% Verschnitt)",
                    "Gesamtpreis": f"{material_cost:.2f} €"
                })
            
            # Zubehör
            for accessory, data in accessories.get(component, {}).items():
                accessory_data = current_accessories_db[current_accessories_db['accessory'] == accessory].iloc[0]
                accessory_price = float(accessory_data['price'])
                accessory_cost = data['cost']
                total_accessory_cost += accessory_cost
                component_total_cost += accessory_cost
                table_data.append({
                    "Beschreibung": f"Zubehör: {accessory}",
                    "Menge": f"{data['amount']} Stück",
                    "Einzelpreis": f"{accessory_price:.2f} €",
                    "Gesamtpreis": f"{accessory_cost:.2f} €"
                })
            
            # Arbeitsstunden
            component_work_hours = work_hours.get(component, 0)
            component_labor_cost = component_work_hours * current_hourly_rate
            total_labor_cost += component_labor_cost
            component_total_cost += component_labor_cost
            table_data.append({
                "Beschreibung": f"Arbeitsstunden: {component}",
                "Menge": f"{component_work_hours:.2f} h",
                "Einzelpreis": f"{current_hourly_rate:.2f} €",
                "Gesamtpreis": f"{component_labor_cost:.2f} €"
            })
            
            # Gesamtkosten pro Komponente
            table_data.append({
                "Beschreibung": f"Gesamtkosten: {component}",
                "Menge": "-",
                "Einzelpreis": "-",
                "Gesamtpreis": f"{component_total_cost:.2f} €"
            })
        
        # Gesamtkosten
        total_cost = total_material_cost + total_accessory_cost + total_labor_cost + current_overhead_costs + (consultation_hours * current_hourly_rate)
        profit_amount = total_cost * (current_profit_margin / 100)
        final_price = total_cost + profit_amount
        
        table_data.append({"Beschreibung": "Gesamtmaterialkosten", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": f"{total_material_cost:.2f} €"})
        table_data.append({"Beschreibung": "Gesamtzubehörkosten", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": f"{total_accessory_cost:.2f} €"})
        table_data.append({"Beschreibung": "Gesamtarbeitskosten", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": f"{total_labor_cost:.2f} €"})
        table_data.append({"Beschreibung": "Gesamtproduktionskosten", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": f"{total_cost:.2f} €"})
        table_data.append({"Beschreibung": f"Gewinnbetrag ({current_profit_margin}%)", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": f"{profit_amount:.2f} €"})
        table_data.append({"Beschreibung": "Empfohlener Verkaufspreis", "Menge": "-", "Einzelpreis": "-", "Gesamtpreis": f"{final_price:.2f} €"})
        
        # Erstellen und Anzeigen der Tabelle
        df = pd.DataFrame(table_data)

        # Styling der Dataframe
        def highlight_rows(row):
            if row['Beschreibung'].startswith('Komponente:'):
                return ['background-color: #FFF9C4; color: black;'] * len(row)
            elif row['Beschreibung'].startswith('Gesamtkosten:'):
                return ['background-color: #C8E6C9; color: black;'] * len(row)
            elif row['Beschreibung'] == 'Empfohlener Verkaufspreis':
                return ['background-color: #BBDEFB; color: black; font-weight: bold'] * len(row)
            return [''] * len(row)

        # Formatierung der Zahlen
        df['Menge'] = df['Menge'].apply(lambda x: f"{x:,.2f}".replace(',', ' ').replace('.', ',') if isinstance(x, (int, float)) else x)
        df['Einzelpreis'] = df['Einzelpreis'].apply(lambda x: f"{x:,.2f} €".replace(',', ' ').replace('.', ',') if isinstance(x, (int, float)) else x)
        df['Gesamtpreis'] = df['Gesamtpreis'].apply(lambda x: f"{x:,.2f} €".replace(',', ' ').replace('.', ',') if isinstance(x, (int, float)) else x)

        styled_df = df.style.apply(highlight_rows, axis=1)
        styled_df = styled_df.set_properties(**{
            'background-color': '#2B2B2B',
            'color': 'white',
            'border-color': 'white'
        })
        styled_df = styled_df.set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#1E1E1E'), ('color', 'white')]},
            {'selector': 'td', 'props': [('text-align', 'right')]},
            {'selector': 'td:first-child', 'props': [('text-align', 'left')]},
        ])

        # Anzeigen der Dataframe
        st.markdown(
            styled_df.to_html(),
            unsafe_allow_html=True
        )

        if st.button('Outfit löschen', key=f"delete_{outfit['id']}"):
            delete_outfit(supabase_manager, outfit['id'])
            st.success(f"Outfit '{outfit['name']}' wurde gelöscht. Bitte laden Sie die Seite neu, um die Änderungen zu sehen.")
            st.rerun()

    except Exception as e:
        logger.error(f"Fehler beim Laden des Outfits: {e}")
        st.error(f"Fehler beim Laden des Outfits: {e}")
        st.error(f"Problematische Daten: {outfit}")




def delete_outfit(supabase_manager: SupabaseManager, outfit_id: int) -> None:
    """
    Löscht ein Outfit aus der Datenbank.
    
    Args:
        supabase_manager (SupabaseManager): Der Supabase-Manager für Datenbankoperationen.
        outfit_id (int): ID des zu löschenden Outfits.
    """
    try:
        supabase_manager.client.table('saved_outfits').delete().eq('id', outfit_id).execute()
        st.success(f"Outfit mit ID {outfit_id} erfolgreich gelöscht!")
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Outfits: {e}")
        st.error(f"Fehler beim Löschen des Outfits: {e}")


def update_all_outfits(outfits: pd.DataFrame, current_hourly_rate: float, current_overhead_costs: float, current_profit_margin: float, consultation_hours: float) -> None:
    """
    Aktualisiert alle Outfits mit den aktuellen Einstellungen.
    
    Args:
        outfits (pd.DataFrame): DataFrame mit allen Outfits.
        current_hourly_rate (float): Aktueller Stundensatz.
        current_overhead_costs (float): Aktuelle Gemeinkosten.
        current_profit_margin (float): Aktuelle Gewinnmarge.
        consultation_hours (float): Beratungsstunden.
    """
    updated_outfits = []
    for _, outfit in outfits.iterrows():
        try:
            components = json.loads(outfit['components'])
            materials = json.loads(outfit['materials'])
            accessories = json.loads(outfit['accessories'])
            work_hours = json.loads(outfit['work_hours'])
            
            total_material_cost = sum(sum(item['cost'] for item in component.values()) for component in materials.values())
            total_accessory_cost = sum(sum(item['cost'] for item in component.values()) for component in accessories.values())
            total_labor_cost = sum(float(hours) * current_hourly_rate for hours in work_hours.values())
            consultation_costs = consultation_hours * current_hourly_rate
            
            total_cost = total_material_cost + total_accessory_cost + total_labor_cost + current_overhead_costs + consultation_costs
            profit_amount = total_cost * (current_profit_margin / 100)
            final_price = total_cost + profit_amount

            updated_outfit = {
                'id': int(outfit['id']),
                'name': outfit['name'],
                'components': json.dumps(components),
                'materials': json.dumps(materials),
                'accessories': json.dumps(accessories),
                'work_hours': json.dumps(work_hours),
                'hourly_rate': current_hourly_rate,
                'overhead_costs': current_overhead_costs,
                'consultation_costs': consultation_costs,
                'material_costs': total_material_cost,
                'accessory_costs': total_accessory_cost,
                'labor_costs': total_labor_cost,
                'total_cost': total_cost,
                'profit_margin': current_profit_margin,
                'profit_amount': profit_amount,
                'final_price': final_price,
                'category': outfit['category']
            }
            updated_outfits.append(updated_outfit)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Outfits {outfit['name']}: {e}")
            st.error(f"Fehler beim Aktualisieren des Outfits {outfit['name']}: {e}")
    
    if updated_outfits:
        try:
            supabase_manager.client.table('saved_outfits').upsert(updated_outfits).execute()
            st.success(f"{len(updated_outfits)} Outfits wurden erfolgreich aktualisiert.")
        except Exception as e:
            logger.error(f"Fehler beim Massenupdate der Outfits: {e}")
            st.error(f"Fehler beim Massenupdate der Outfits: {e}")

def generate_csv_download(saved_outfits: pd.DataFrame) -> None:
    """
    Generiert und bietet einen CSV-Download für die gespeicherten Outfits an.
    
    Args:
        saved_outfits (pd.DataFrame): DataFrame mit allen gespeicherten Outfits.
    """
    csv_string = create_formatted_csv(saved_outfits)
    st.download_button(
        label="CSV herunterladen",
        data=csv_string,
        file_name="formatted_outfits.csv",
        mime="text/csv"
    )

def create_formatted_csv(saved_outfits: pd.DataFrame) -> str:
    """
    Erstellt einen formatierten CSV-String aus den gespeicherten Outfits.
    
    Args:
        saved_outfits (pd.DataFrame): DataFrame mit allen gespeicherten Outfits.
    
    Returns:
        str: Formatierter CSV-String.
    """
    df = saved_outfits.copy()
    for column in df.columns:
        if df[column].dtype == float:
            df[column] = df[column].apply(lambda x: f"{x:.2f}".replace('.', ','))
        elif df[column].dtype == object:
            df[column] = df[column].apply(serialize_json_data)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding='utf-8', quoting=csv.QUOTE_NONNUMERIC, sep=';')
    return buffer.getvalue()

def serialize_json_data(data: Any) -> str:
    """
    Serialisiert JSON-Daten zu einem formatierten String.
    
    Args:
        data (Any): Zu serialisierende Daten.
    
    Returns:
        str: Serialisierte Daten als String.
    """
    try:
        parsed = json.loads(data)
        formatted = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
        return formatted
    except (json.JSONDecodeError, TypeError):
        return str(data)

def analyze_outfits(saved_outfits: pd.DataFrame) -> None:
    """
    Analysiert die gespeicherten Outfits und zeigt Statistiken an.
    
    Args:
        saved_outfits (pd.DataFrame): DataFrame mit allen gespeicherten Outfits.
    """
    if saved_outfits.empty:
        st.write("Keine Daten verfügbar.")
        return

    saved_outfits['total_material_cost'] = saved_outfits['material_costs'] + saved_outfits['accessory_costs']
    
    analysis = saved_outfits.groupby('category').agg({
        'total_material_cost': 'mean',
        'work_hours': lambda x: pd.Series([sum(json.loads(hours).values()) for hours in x]).mean()
    }).reset_index()

    analysis.columns = ['Kategorie', 'Durchschnittliche Materialkosten (€)', 'Durchschnittliche Arbeitsstunden']

    st.subheader("Analyse der Outfits nach Kategorie")
    st.table(analysis)

    for category in saved_outfits['category'].unique():
        with st.expander(f"Details für Kategorie: {category}"):
            category_entries = saved_outfits[saved_outfits['category'] == category][['name', 'total_material_cost', 'work_hours']]
            category_entries['work_hours'] = category_entries['work_hours'].apply(lambda hours: sum(json.loads(hours).values()))
            st.table(category_entries)

def main():
    st.set_page_config(page_title="Outfit-Preis-Kalkulator  ")
    page_icon="🧵",  # Sie können hier ein passendes Emoji oder einen Pfad zu einem Icon verwenden
    st.title('Outfit-Preis-Kalkulator')

    supabase_manager = SupabaseManager()
    ui_manager = UIManager()
    outfit_calculator = OutfitCalculator()

    # Sidebar-Einstellungen
    hourly_rate, fixed_costs, outfits_per_month, consultation_hours, profit_margin = ui_manager.display_sidebar()

    # Daten laden
    materials_db = supabase_manager.load_cached_data('materials')
    accessories_db = supabase_manager.load_cached_data('accessories')

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Kalkulator", "Materialien verwalten", "Zubehör verwalten", "Gespeicherte Outfits", "Analysen", "Hilfe"])

    with tab1:
        st.subheader('Outfit-Komponenten')
        components = [component for component in ALL_POSSIBLE_COMPONENTS if st.checkbox(component, key=f"component_{component}")]

        overhead_costs = fixed_costs / outfits_per_month
        consultation_costs = consultation_hours * hourly_rate
        st.write(f'Gemeinkosten pro Outfit: {overhead_costs:.2f} €')
        st.write(f'Beratungskosten: {consultation_costs:.2f} €')
        st.divider()

        component_costs = {component: {'Materialien': {}, 'Zubehör': {}, 'Arbeitskosten': 0} for component in ALL_POSSIBLE_COMPONENTS}

        for component in components:
            with st.expander(f'{component} Details', expanded=True):
                material_tab, accessory_tab, cost_breakdown_tab = st.tabs(["Materialien", "Zubehör", "Kostenaufschlüsselung"])
                
                with material_tab:
                    material_count = st.session_state.get(f'{component}_material_count', 1)
                    for i in range(material_count):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            material = st.selectbox('Material', options=[''] + materials_db['material'].tolist(), key=f'{component}_material_{i}')
                        with col2:
                            amount = st.number_input('Menge (m)', min_value=0.0, key=f'{component}_material_amount_{i}', step=0.1)
                        with col3:
                            if material:
                                material_data = materials_db[materials_db['material'] == material].iloc[0]
                                material_price = float(material_data['average_price'])
                                material_waste = float(material_data['waste_percentage']) / 100
                                material_cost = amount * material_price * (1 + material_waste)
                                component_costs[component]['Materialien'][material] = {'amount': amount, 'cost': material_cost}
                                st.markdown(f'<div style="text-align: right;">{material_cost:.2f} €</div>', unsafe_allow_html=True)
                        with col4:
                            if st.button('X', key=f'{component}_remove_material_{i}'):
                                if f'{component}_material_{i}' in st.session_state:
                                    del st.session_state[f'{component}_material_{i}']
                                if f'{component}_material_amount_{i}' in st.session_state:
                                    del st.session_state[f'{component}_material_amount_{i}']
                                st.session_state[f'{component}_material_count'] = max(1, material_count - 1)
                                st.rerun()
                    if st.button('Material hinzufügen', key=f'{component}_add_material'):
                        st.session_state[f'{component}_material_count'] = material_count + 1
                        st.rerun()

                with accessory_tab:
                    accessory_count = st.session_state.get(f'{component}_accessory_count', 1)
                    for i in range(accessory_count):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            accessory = st.selectbox('Zubehör', options=[''] + accessories_db['accessory'].tolist(), key=f'{component}_accessory_{i}')
                        with col2:
                            amount = st.number_input('Menge', min_value=0, key=f'{component}_accessory_amount_{i}', step=1)
                        with col3:
                            if accessory:
                                accessory_data = accessories_db[accessories_db['accessory'] == accessory].iloc[0]
                                accessory_price = float(accessory_data['price'])
                                accessory_cost = amount * accessory_price
                                component_costs[component]['Zubehör'][accessory] = {'amount': amount, 'cost': accessory_cost}
                                st.markdown(f'<div style="text-align: right;">{accessory_cost:.2f} €</div>', unsafe_allow_html=True)
                        with col4:
                            if st.button('X', key=f'{component}_remove_accessory_{i}'):
                                if f'{component}_accessory_{i}' in st.session_state:
                                    del st.session_state[f'{component}_accessory_{i}']
                                if f'{component}_accessory_amount_{i}' in st.session_state:
                                    del st.session_state[f'{component}_accessory_amount_{i}']
                                st.session_state[f'{component}_accessory_count'] = max(1, accessory_count - 1)
                                st.rerun()
                    if st.button('Zubehör hinzufügen', key=f'{component}_add_accessory'):
                        st.session_state[f'{component}_accessory_count'] = accessory_count + 1
                        st.rerun()

                with cost_breakdown_tab:
                    st.subheader('Kostenaufschlüsselung')
                    st.write('Materialien:')
                    for material, data in component_costs[component]['Materialien'].items():
                        st.write(f'- {material}: {data["cost"]:.2f} €')
                    st.write('Zubehör:')
                    for accessory, data in component_costs[component]['Zubehör'].items():
                        st.write(f'- {accessory}: {data["cost"]:.2f} €')
                    work_hours = st.number_input(f'Arbeitsstunden für {component}', min_value=0.0, step=0.5, key=f'{component}_work_hours')
                    labor_cost = work_hours * hourly_rate
                    component_costs[component]['Arbeitskosten'] = labor_cost
                    st.write(f'Arbeitskosten: {labor_cost:.2f} €')
                    component_total = sum(data["cost"] for data in component_costs[component]['Materialien'].values()) + \
                                      sum(data["cost"] for data in component_costs[component]['Zubehör'].values()) + \
                                      component_costs[component]['Arbeitskosten']
                    st.write(f'Gesamtkosten für {component}: {component_total:.2f} €')

        st.divider()
        st.subheader('Gesamtübersicht')
        cost_data, total_material_cost, total_accessory_cost, total_labor_cost, total_cost, profit_amount, final_price = outfit_calculator.calculate_costs(
            components, component_costs, materials_db, accessories_db, hourly_rate, overhead_costs, consultation_costs, profit_margin
        )

        ui_manager.display_cost_overview(cost_data)

        costs = [total_material_cost, total_accessory_cost, total_labor_cost, overhead_costs, consultation_costs]
        labels = ['Materialien', 'Zubehör', 'Arbeitskosten', 'Gemeinkosten', 'Beratung']
        ui_manager.create_pie_chart(costs, labels)

        st.divider()
        st.subheader("Outfit speichern")
        outfit_name = st.text_input('Outfit-Name')
        category = st.selectbox('Kategorie', ['Basics', 'Made-to-Order'])

        if st.button('Outfit speichern') and outfit_name:
            if not components:
                st.error("Bitte wählen Sie mindestens eine Komponente aus.")
            elif not outfit_name.strip():
                st.error("Bitte geben Sie einen gültigen Outfit-Namen ein.")
            else:
                with st.spinner('Outfit wird gespeichert...'):
                    outfit_components = {component: {
                        'materials': {m: {'amount': data['amount'], 'cost': data['cost']} for m, data in component_costs[component]['Materialien'].items()},
                        'accessories': {a: {'amount': data['amount'], 'cost': data['cost']} for a, data in component_costs[component]['Zubehör'].items()},
                        'work_hours': component_costs[component]['Arbeitskosten'] / hourly_rate
                    } for component in components}
                    
                    outfit_data = {
                        'name': outfit_name,
                        'components': json.dumps(components),
                        'materials': json.dumps({c: outfit_components[c]['materials'] for c in components}),
                        'accessories': json.dumps({c: outfit_components[c]['accessories'] for c in components}),
                        'work_hours': json.dumps({c: outfit_components[c]['work_hours'] for c in components}),
                        'hourly_rate': hourly_rate,
                        'overhead_costs': overhead_costs,
                        'consultation_costs': consultation_costs,
                        'material_costs': total_material_cost,
                        'accessory_costs': total_accessory_cost,
                        'labor_costs': total_labor_cost,
                        'total_cost': total_cost,
                        'profit_margin': profit_margin,
                        'profit_amount': profit_amount,
                        'final_price': final_price,
                        'category': category
                    }
                    supabase_manager.save_outfit(outfit_data)

    with tab2:
        st.subheader('Materialien verwalten')
        
        with st.form(key='add_material_form'):
            material_name = st.text_input('Materialname')
            average_price = st.number_input('Durchschnittspreis (€)', min_value=0.0, step=0.01)
            waste_percentage = st.number_input('Abfallprozentsatz (%)', min_value=0.0, step=0.1)
            submit_button = st.form_submit_button(label='Material hinzufügen')
            
            if submit_button:
                add_material(supabase_manager, material_name, average_price, waste_percentage)
        
        st.write("Vorhandene Materialien:")
        for index, row in materials_db.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.text(row['material'])
            with col2:
                new_price = st.number_input('Preis (€)', value=float(row['average_price']), key=f"price_{index}", step=0.01)
            with col3:
                new_waste = st.number_input('Abfall (%)', value=float(row['waste_percentage']), key=f"waste_{index}", step=0.1)
            with col4:
                if st.button('Löschen', key=f"delete_material_{index}"):
                    supabase_manager.delete_material(row['material'])
                    st.rerun()
            if new_price != row['average_price'] or new_waste != row['waste_percentage']:
                materials_db.at[index, 'average_price'] = new_price
                materials_db.at[index, 'waste_percentage'] = new_waste
                supabase_manager.update_data(materials_db, 'materials')

    with tab3:
        st.subheader('Zubehör verwalten')
        
        with st.form(key='add_accessory_form'):
            accessory_name = st.text_input('Zubehörname')
            price = st.number_input('Preis (€)', min_value=0.0, step=0.01)
            submit_button = st.form_submit_button(label='Zubehör hinzufügen')
            
            if submit_button:
                add_accessory(supabase_manager, accessory_name, price)
        
        st.write("Vorhandenes Zubehör:")
        for index, row in accessories_db.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(row['accessory'])
            with col2:
                new_price = st.number_input('Preis (€)', value=float(row['price']), key=f"accessory_price_{index}", step=0.01)
            with col3:
                if st.button('Löschen', key=f"delete_accessory_{index}"):
                    supabase_manager.delete_accessory(row['accessory'])
                    st.rerun()
            if new_price != row['price']:
                accessories_db.at[index, 'price'] = new_price
                supabase_manager.update_data(accessories_db, 'accessories')

    with tab4:
        st.subheader('Gespeicherte Outfits')
        saved_outfits = supabase_manager.load_data('saved_outfits')
        display_saved_outfits(supabase_manager, ui_manager, hourly_rate, overhead_costs, materials_db, accessories_db, profit_margin, consultation_hours)

    with tab5:
        st.subheader('Analysen')
        saved_outfits = supabase_manager.load_data('saved_outfits')
        analyze_outfits(saved_outfits)

    with tab6:
        st.subheader('Hilfe')
        st.write("""
        Willkommen beim Outfit-Preis-Kalkulator!

        So verwenden Sie diese App:

        1. Im 'Kalkulator' Tab:
        - Geben Sie die grundlegenden Informationen ein (Stundensatz, Fixkosten, etc.).
        - Wählen Sie die Outfit-Komponenten aus.
        - Fügen Sie für jede Komponente Materialien und Zubehör hinzu.
        - Sehen Sie sich die Gesamtübersicht und Kostenverteilung an.
        - Speichern Sie das Outfit mit einem Namen.

        2. Im 'Materialien verwalten' Tab:
        - Fügen Sie neue Materialien hinzu, bearbeiten oder löschen Sie bestehende.
        - Änderungen werden automatisch gespeichert.

        3. Im 'Zubehör verwalten' Tab:
        - Fügen Sie neues Zubehör hinzu, bearbeiten oder löschen Sie bestehendes.
        - Änderungen werden automatisch gespeichert.

        4. Im 'Gespeicherte Outfits' Tab:
        - Sehen Sie sich Ihre gespeicherten Outfits an.
        - Die Preise werden automatisch basierend auf den aktuellen Parametern aktualisiert.
        - Exportieren Sie die Daten als CSV-Datei.

        5. Im 'Analysen' Tab:
        - Sehen Sie sich Analysen Ihrer gespeicherten Outfits an.

        Alle Änderungen werden automatisch in der Datenbank gespeichert und stehen allen Benutzern zur Verfügung.

        Bei Fragen oder Problemen wenden Sie sich bitte an den Support.
        """)


if __name__ == "__main__":
    main()

