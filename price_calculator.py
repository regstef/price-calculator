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


# Laden der Umgebungsvariablen
load_dotenv()

# Sichere Datenbankverbindung
supabase_url = "https://qormgjgpisbzyegipbiq.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFvcm1namdwaXNienllZ2lwYmlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjkxODY2NjMsImV4cCI6MjA0NDc2MjY2M30.JB7xuS8R8nBShuTYm5LmZifHR7SpsEYxcVOaag8uRKI"
supabase: Client = create_client(supabase_url, supabase_key)

def load_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        if response.data is None:
            st.error(f"Fehler beim Laden der Daten aus {table_name}: {response}")
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {str(e)}")
        return pd.DataFrame()

def update_data(data, table_name):
    try:
        for index, row in data.iterrows():
            supabase.table(table_name).upsert(row.to_dict()).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren der Daten: {str(e)}")
        return False

def save_data(data, table_name):
    updated = update_data(data, table_name)
    if updated:
        st.success(f'Daten in {table_name} aktualisiert!')
    else:
        st.error(f'Fehler beim Aktualisieren der Daten in {table_name}.')

def sanitize_input(input_string):
    return ''.join(char for char in input_string if char.isalnum() or char.isspace())

def save_outfit(name, components, materials, accessories, work_hours, hourly_rate, overhead_costs, consultation_costs, material_costs, accessory_costs, labor_costs, total_cost, profit_margin, profit_amount, final_price, category):
    try:
        supabase.table('saved_outfits').insert({
            'name': sanitize_input(name),
            'components': json.dumps(components),
            'materials': json.dumps(materials),
            'accessories': json.dumps(accessories),
            'work_hours': json.dumps(work_hours),
            'hourly_rate': hourly_rate,
            'overhead_costs': overhead_costs,
            'consultation_costs': consultation_costs,
            'material_costs': material_costs,
            'accessory_costs': accessory_costs,
            'labor_costs': labor_costs,
            'total_cost': total_cost,
            'profit_margin': profit_margin,
            'profit_amount': profit_amount,
            'final_price': final_price,
            'category': category
        }).execute()
        st.success(f"Outfit '{name}' erfolgreich gespeichert!")
    except Exception as e:
        st.error(f"Fehler beim Speichern des Outfits: {str(e)}")

def delete_outfit(id):
    try:
        supabase.table('saved_outfits').delete().eq('id', id).execute()
        st.success(f"Outfit mit ID {id} erfolgreich gelöscht!")
    except Exception as e:
        st.error(f"Fehler beim Löschen des Outfits: {str(e)}")

def delete_material(material_name):
    try:
        supabase.table('materials').delete().eq('material', material_name).execute()
        st.success(f"Material '{material_name}' erfolgreich gelöscht!")
    except Exception as e:
        st.error(f"Fehler beim Löschen des Materials: {str(e)}")

def delete_accessory(accessory_name):
    try:
        supabase.table('accessories').delete().eq('accessory', accessory_name).execute()
        st.success(f"Zubehör '{accessory_name}' erfolgreich gelöscht!")
    except Exception as e:
        st.error(f"Fehler beim Löschen des Zubehörs: {str(e)}")

def format_currency(value):
    return f"{value:.2f} €"

@st.cache_data
def get_saved_outfits_from_database():
    try:
        response = supabase.table('saved_outfits').select("*").execute()
        if response.data is None:
            st.error("Fehler beim Abrufen der gespeicherten Outfits.")
            return []
        return response.data
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {str(e)}")
        return []

def format_decimal(value):
    if isinstance(value, float):
        return f"{value:.2f}".replace('.', ',')
    return value

def serialize_json_data(data):
    try:
        parsed = json.loads(data)
        formatted = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
        return formatted
    except (json.JSONDecodeError, TypeError):
        return data

def create_formatted_csv(saved_outfits):
    df = pd.DataFrame(saved_outfits)
    for column in df.columns:
        if df[column].dtype == float:
            df[column] = df[column].apply(format_decimal)
        elif df[column].dtype == object:
            df[column] = df[column].apply(serialize_json_data)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding='utf-8', quoting=csv.QUOTE_NONNUMERIC, sep=';')
    return buffer.getvalue()

def generate_csv_download():
    saved_outfits = get_saved_outfits_from_database()
    csv_string = create_formatted_csv(saved_outfits)
    st.download_button(
        label="CSV herunterladen",
        data=csv_string,
        file_name="formatted_outfits.csv",
        mime="text/csv"
    )

def analyze_outfits():
    saved_outfits = load_data('saved_outfits')
    
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

def create_cost_overview(components, component_costs, materials_db, accessories_db, hourly_rate, overhead_costs, consultation_costs, profit_margin):
    if not components:
        st.warning("Keine Komponenten ausgewählt. Bitte wählen Sie mindestens eine Komponente aus.")
        return [], 0, 0, 0, 0, 0, 0

    cost_data = []
    total_material_cost = 0
    total_accessory_cost = 0
    total_labor_cost = 0

    for component in components:
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
                'Betrag (€)': format_currency(cost)
            })

    cost_data.append({
        'Kategorie': 'Gesamtmaterialkosten',
        'Komponente': '',
        'Beschreibung': '',
        'Betrag (€)': format_currency(total_material_cost)
    })

    for component in components:
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
                'Betrag (€)': format_currency(cost)
            })

    cost_data.append({
        'Kategorie': 'Gesamtzubehörkosten',
        'Komponente': '',
        'Beschreibung': '',
        'Betrag (€)': format_currency(total_accessory_cost)
    })

    for component in components:
        work_hours = component_costs[component]['Arbeitskosten'] / hourly_rate if isinstance(component_costs[component]['Arbeitskosten'], (int, float)) else 0
        labor_cost = work_hours * hourly_rate
        total_labor_cost += labor_cost
        cost_data.append({
            'Kategorie': 'Arbeitskosten',
            'Komponente': component,
            'Beschreibung': f"{work_hours:.2f} Stunden",
            'Betrag (€)': format_currency(labor_cost)
        })

    cost_data.append({
        'Kategorie': 'Gesamtarbeitskosten',
        'Komponente': '',
        'Beschreibung': '',
        'Betrag (€)': format_currency(total_labor_cost)
    })

    cost_data.extend([
        {'Kategorie': 'Zusätzliche Kosten', 'Komponente': '-', 'Beschreibung': 'Gemeinkosten', 'Betrag (€)': format_currency(overhead_costs)},
        {'Kategorie': 'Zusätzliche Kosten', 'Komponente': '-', 'Beschreibung': 'Beratungskosten', 'Betrag (€)': format_currency(consultation_costs)}
    ])

    total_cost = total_material_cost + total_accessory_cost + total_labor_cost + overhead_costs + consultation_costs

    profit_amount = total_cost * (profit_margin / 100)
    final_price = total_cost + profit_amount

    cost_data.extend([
        {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Gesamtproduktionskosten', 'Betrag (€)': format_currency(total_cost)},
        {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': f'Gewinnbetrag ({profit_margin}%)', 'Betrag (€)': format_currency(profit_amount)},
        {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Empfohlener Verkaufspreis', 'Betrag (€)': format_currency(final_price)}
    ])

    return cost_data, total_material_cost, total_accessory_cost, total_labor_cost, total_cost, profit_amount, final_price

def create_pie_chart(costs, labels):
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
        st.error(f"Fehler bei der Erstellung des Kuchendiagramms: {str(e)}")
        st.write("Kostendaten:", positive_costs)
        st.write("Labels:", positive_labels)

def update_all_outfits(outfits, current_hourly_rate, current_overhead_costs, current_profit_margin, consultation_hours):
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
                'id': int(outfit['id']),  # Konvertiere zu int
                'name': outfit['name'],  # Füge den Namen hinzu
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
            st.error(f"Fehler beim Aktualisieren des Outfits {outfit['name']}: {str(e)}")
    
    # Batch update all outfits
    if updated_outfits:
        try:
            supabase.table('saved_outfits').upsert(updated_outfits).execute()
            st.success(f"{len(updated_outfits)} Outfits wurden erfolgreich aktualisiert.")
        except Exception as e:
            st.error(f"Fehler beim Massenupdate der Outfits: {str(e)}")
    

def display_saved_outfits(current_hourly_rate, current_overhead_costs, current_materials_db, current_accessories_db, current_profit_margin, consultation_hours=2.0):
    # Laden Sie die Outfits immer neu aus der Datenbank
    saved_outfits = load_data('saved_outfits')
    
    if saved_outfits.empty:
        st.write("Keine Outfits gespeichert.")
    else:
        # Suchfunktion
        search_term = st.text_input("Suche nach Outfit-Namen")
        
        # Filter
        category_filter = st.multiselect("Nach Kategorie filtern", options=['Basics', 'Made-to-Order'])
        
        # Sortierung
        sort_column = st.selectbox("Sortieren nach", options=['name', 'category', 'final_price'])
        sort_order = st.radio("Sortierreihenfolge", options=['Aufsteigend', 'Absteigend'])
        
        # Filtern und Sortieren der Daten
        filtered_outfits = saved_outfits
        if search_term:
            filtered_outfits = filtered_outfits[filtered_outfits['name'].str.contains(search_term, case=False)]
        if category_filter:
            filtered_outfits = filtered_outfits[filtered_outfits['category'].isin(category_filter)]
        
        filtered_outfits = filtered_outfits.sort_values(by=sort_column, ascending=(sort_order == 'Aufsteigend'))
        
        # Tabellarische Übersicht
        st.table(filtered_outfits[['name', 'category', 'final_price']])
        
        # Detailansicht für ausgewähltes Outfit
        selected_outfit = st.selectbox("Outfit-Details anzeigen", options=filtered_outfits['name'])
        if selected_outfit:
            outfit = filtered_outfits[filtered_outfits['name'] == selected_outfit].iloc[0]
            with st.expander(f"Details für {selected_outfit}", expanded=True):
                display_outfit_details(outfit, current_hourly_rate, current_overhead_costs, current_materials_db, current_accessories_db, current_profit_margin, consultation_hours)
            
            # Button zum Bearbeiten des ausgewählten Outfits
            if st.button(f"Outfit '{selected_outfit}' bearbeiten"):
                st.session_state.editing_outfit = outfit
                st.rerun()

        # Bearbeitungsmodus
        if 'editing_outfit' in st.session_state:
            edit_outfit(st.session_state.editing_outfit, current_materials_db, current_accessories_db, 
                        current_hourly_rate, current_overhead_costs, current_profit_margin, consultation_hours)

        # Buttons am Ende der Seite
        st.write("---")  # Trennlinie
        col1, col2 = st.columns(2)
        with col1:
            if st.button('Alle Outfits aktualisieren'):
                with st.spinner('Outfits werden aktualisiert...'):
                    update_all_outfits(saved_outfits, current_hourly_rate, current_overhead_costs, current_profit_margin, consultation_hours)
                st.success("Alle Outfits wurden erfolgreich aktualisiert.")
                # Daten neu laden
                saved_outfits = load_data('saved_outfits')
                st.rerun()
        with col2:
            if st.button('CSV erstellen'):
                generate_csv_download()




class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        elif isinstance(obj, np.generic):
            return obj.item()
        return super(NumpyEncoder, self).default(obj)

def serialize_to_json(data):
    return json.dumps(data, cls=NumpyEncoder)

def parse_json(json_str):
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return json_str

def edit_outfit(outfit, materials_db, accessories_db, current_hourly_rate, current_overhead_costs, current_profit_margin, consultation_hours):
    st.subheader(f"Outfit '{outfit['name']}' bearbeiten")
    
    new_name = st.text_input("Name", value=outfit['name'], key=f"edit_name_{outfit['id']}")
    new_category = st.selectbox("Kategorie", options=['Basics', 'Made-to-Order'], 
                                index=['Basics', 'Made-to-Order'].index(outfit['category']),
                                key=f"edit_category_{outfit['id']}")
    
    components = parse_json(outfit['components'])
    materials = parse_json(outfit['materials'])
    accessories = parse_json(outfit['accessories'])
    work_hours = parse_json(outfit['work_hours'])
    
    st.subheader("Komponenten")
    new_components = st.multiselect("Komponenten", options=['Kleid', 'Jacke', 'Oberteil', 'Hose', 'Rock', 'Overall'], 
                                    default=components, key=f"edit_components_{outfit['id']}")
    
    new_materials = {}
    new_accessories = {}
    new_work_hours = {}
    
    total_material_cost = 0
    total_accessory_cost = 0
    total_labor_cost = 0
    
    for component in new_components:
        st.subheader(f"Details für {component}")
        new_work_hours[component] = st.number_input(f"Arbeitsstunden für {component}", 
                                                    value=float(work_hours.get(component, 0)), 
                                                    min_value=0.0, step=0.5,
                                                    key=f"edit_hours_{outfit['id']}_{component}")
        total_labor_cost += new_work_hours[component] * current_hourly_rate
        
        st.write("Materialien")
        component_materials = materials.get(component, {})
        new_materials[component] = {}
        for material, data in component_materials.items():
            new_amount = st.number_input(f"Menge für {material} (m)", 
                                         value=float(data['amount']), 
                                         min_value=0.0, step=0.1,
                                         key=f"edit_material_{outfit['id']}_{component}_{material}")
            material_price = float(materials_db[materials_db['material'] == material]['average_price'].iloc[0])
            material_waste = float(materials_db[materials_db['material'] == material]['waste_percentage'].iloc[0]) / 100
            material_cost = new_amount * material_price * (1 + material_waste)
            new_materials[component][material] = {'amount': new_amount, 'cost': material_cost}
            total_material_cost += material_cost
        
        st.write("Zubehör")
        component_accessories = accessories.get(component, {})
        new_accessories[component] = {}
        for accessory, data in component_accessories.items():
            new_amount = st.number_input(f"Menge für {accessory}", 
                                         value=int(data['amount']), 
                                         min_value=0, step=1,
                                         key=f"edit_accessory_{outfit['id']}_{component}_{accessory}")
            accessory_price = float(accessories_db[accessories_db['accessory'] == accessory]['price'].iloc[0])
            accessory_cost = new_amount * accessory_price
            new_accessories[component][accessory] = {'amount': new_amount, 'cost': accessory_cost}
            total_accessory_cost += accessory_cost
    
    total_cost = total_material_cost + total_accessory_cost + total_labor_cost + current_overhead_costs + (consultation_hours * current_hourly_rate)
    profit_amount = total_cost * (current_profit_margin / 100)
    final_price = total_cost + profit_amount
    
    if st.button("Änderungen speichern", key=f"save_changes_{outfit['id']}"):
        updated_outfit = {
            'id': int(outfit['id']),
            'name': new_name,
            'category': new_category,
            'components': serialize_to_json(new_components),
            'materials': serialize_to_json(new_materials),
            'accessories': serialize_to_json(new_accessories),
            'work_hours': serialize_to_json(new_work_hours),
            'hourly_rate': current_hourly_rate,
            'overhead_costs': current_overhead_costs,
            'consultation_costs': consultation_hours * current_hourly_rate,
            'material_costs': total_material_cost,
            'accessory_costs': total_accessory_cost,
            'labor_costs': total_labor_cost,
            'total_cost': total_cost,
            'profit_margin': current_profit_margin,
            'profit_amount': profit_amount,
            'final_price': final_price
        }
        
        try:
            supabase.table('saved_outfits').update(updated_outfit).eq('id', int(outfit['id'])).execute()
            st.success("Outfit erfolgreich aktualisiert!")
            
            time.sleep(1)
            
            del st.session_state.editing_outfit
            st.rerun()
        except Exception as e:
            st.error(f"Fehler beim Aktualisieren des Outfits: {str(e)}")
            st.error(f"Problematische Daten: {updated_outfit}")
    
    if st.button("Bearbeitung abbrechen", key=f"cancel_edit_{outfit['id']}"):
        del st.session_state.editing_outfit
        st.rerun()


def display_outfit_details(outfit, current_hourly_rate, current_overhead_costs, current_materials_db, current_accessories_db, current_profit_margin, consultation_hours):
    try:
        components = parse_json(outfit['components'])
        materials = parse_json(outfit['materials'])
        accessories = parse_json(outfit['accessories'])
        work_hours = parse_json(outfit['work_hours'])
        
        total_material_cost = sum(sum(item['cost'] for item in component.values()) for component in materials.values())
        total_accessory_cost = sum(sum(item['cost'] for item in component.values()) for component in accessories.values())
        total_labor_cost = sum(float(hours) * current_hourly_rate for hours in work_hours.values())
        consultation_costs = consultation_hours * current_hourly_rate
        
        total_cost = total_material_cost + total_accessory_cost + total_labor_cost + current_overhead_costs + consultation_costs
        profit_amount = total_cost * (current_profit_margin / 100)
        final_price = total_cost + profit_amount

        tab1, tab2, tab3, tab4 = st.tabs(["Allgemeine Informationen", "Komponenten-Details", "Kostenaufschlüsselung", "Konfiguration"])
        
        with tab1:
            cost_data = [
                {'Kategorie': 'Name', 'Wert': outfit['name']},
                {'Kategorie': 'Kategorie', 'Wert': outfit['category']},
                {'Kategorie': 'Gesamtproduktionskosten', 'Wert': format_currency(total_cost)},
                {'Kategorie': f'Gewinnbetrag ({current_profit_margin}%)', 'Wert': format_currency(profit_amount)},
                {'Kategorie': 'Empfohlener Verkaufspreis', 'Wert': format_currency(final_price)}
            ]
            st.table(pd.DataFrame(cost_data))

        with tab2:
            for component in components:
                st.write(f"**{component}**")
                st.write(f"Arbeitszeit: {work_hours.get(component, 0)} Stunden")
                
                st.write("Materialien:")
                for material, data in materials.get(component, {}).items():
                    st.write(f"- {material}: {data['amount']} m, Kosten: {format_currency(data['cost'])}")
                
                st.write("Zubehör:")
                for accessory, data in accessories.get(component, {}).items():
                    st.write(f"- {accessory}: {data['amount']} Stück, Kosten: {format_currency(data['cost'])}")
                
                st.write("---")  # Trennlinie zwischen den Komponenten

        with tab3:
            cost_breakdown = [
                {'Kategorie': 'Materialkosten', 'Wert': format_currency(total_material_cost)},
                {'Kategorie': 'Zubehörkosten', 'Wert': format_currency(total_accessory_cost)},
                {'Kategorie': 'Arbeitskosten', 'Wert': format_currency(total_labor_cost)},
                {'Kategorie': 'Gemeinkosten', 'Wert': format_currency(current_overhead_costs)},
                {'Kategorie': 'Beratungskosten', 'Wert': format_currency(consultation_costs)}
            ]
            st.table(pd.DataFrame(cost_breakdown))

        with tab4:
            config_data = [
                {'Parameter': 'Stundensatz', 'Wert': format_currency(current_hourly_rate)},
                {'Parameter': 'Beratungsstunden', 'Wert': f"{consultation_hours} Stunden"},
                {'Parameter': 'Gemeinkosten', 'Wert': format_currency(current_overhead_costs)},
                {'Parameter': 'Beratungskosten', 'Wert': format_currency(consultation_costs)},
                {'Parameter': 'Gewinnmarge', 'Wert': f"{current_profit_margin}%"}
            ]
            st.table(pd.DataFrame(config_data))

        if st.button('Outfit löschen', key=f"delete_{outfit['id']}"):
            delete_outfit(outfit['id'])
            st.success(f"Outfit '{outfit['name']}' wurde gelöscht. Bitte laden Sie die Seite neu, um die Änderungen zu sehen.")
            st.rerun()  # Fügen Sie diese Zeile hinzu, um die App nach dem Löschen neu zu laden

    except Exception as e:
        st.error(f"Fehler beim Laden des Outfits: {str(e)}")
        st.error(f"Problematische Daten: {outfit}")


def add_material(material_name, average_price, waste_percentage):
    try:
        supabase.table('materials').insert({
            'material': sanitize_input(material_name),
            'average_price': average_price,
            'waste_percentage': waste_percentage
        }).execute()
        st.success(f"Material '{material_name}' erfolgreich hinzugefügt!")
    except Exception as e:
        st.error(f"Fehler beim Hinzufügen des Materials: {str(e)}")

def add_accessory(accessory_name, price):
    try:
        supabase.table('accessories').insert({
            'accessory': sanitize_input(accessory_name),
            'price': price
        }).execute()
        st.success(f"Zubehör '{accessory_name}' erfolgreich hinzugefügt!")
    except Exception as e:
        st.error(f"Fehler beim Hinzufügen des Zubehörs: {str(e)}")

# Hauptanwendung
def main():
    st.set_page_config(page_title="Outfit-Preis-Kalkulator", layout="wide")
    st.title('Outfit-Preis-Kalkulator')

    # Laden der Daten
    materials_db = load_data('materials')
    accessories_db = load_data('accessories')

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Kalkulator", "Materialien verwalten", "Zubehör verwalten", "Gespeicherte Outfits", "Analysen", "Hilfe"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            hourly_rate = st.number_input('Stundensatz (€)', min_value=0.0, value=40.0, step=0.5, help="Der Stundensatz für die Arbeitszeit.")
            fixed_costs = st.number_input('Fixkosten (€)', min_value=0.0, value=1064.0, step=10.0, help="Monatliche Fixkosten des Unternehmens.")
        with col2:
            outfits_per_month = st.number_input('Outfits pro Monat', min_value=1, value=3, step=1, help="Geschätzte Anzahl der produzierten Outfits pro Monat.")
            consultation_hours = st.number_input('Beratungsstunden', min_value=0.0, value=2.0, step=0.5, help="Durchschnittliche Beratungszeit pro Outfit.")

        profit_margin = st.slider('Gewinnmarge (%)', min_value=0, max_value=100, value=20, step=5, help="Gewünschte Gewinnmarge in Prozent.")

        overhead_costs = fixed_costs / outfits_per_month
        consultation_costs = consultation_hours * hourly_rate
        st.write(f'Gemeinkosten pro Outfit: {overhead_costs:.2f} €')
        st.write(f'Beratungskosten: {consultation_costs:.2f} €')
        st.divider()

        all_possible_components = ['Kleid', 'Jacke', 'Oberteil', 'Hose', 'Rock', 'Overall']

        st.subheader('Outfit-Komponenten')
        components = [component for component in all_possible_components if st.checkbox(component, key=f"component_{component}")]

        total_cost = overhead_costs + consultation_costs

        component_costs = {component: {'Materialien': {}, 'Zubehör': {}, 'Arbeitskosten': 0} for component in all_possible_components}

        for component in components:
            with st.expander(f'{component} Details', expanded=True):
                # ... (vorheriger Code bleibt unverändert)
                
                with material_tab:
                    material_count = st.session_state.get(f'{component}_material_count', 1)
                    for i in range(material_count):
                        # ... (vorheriger Code bleibt unverändert)
                        with col4:
                            if st.button('X', key=f'{component}_remove_material_{i}'):
                                if f'{component}_material_{i}' in st.session_state:
                                    del st.session_state[f'{component}_material_{i}']
                                if f'{component}_material_amount_{i}' in st.session_state:
                                    del st.session_state[f'{component}_material_amount_{i}']
                                st.session_state[f'{component}_material_count'] = max(1, material_count - 1)
                                st.rerun()  # Ändern Sie dies von st.experimental_rerun()
                    if st.button('Material hinzufügen', key=f'{component}_add_material'):
                        st.session_state[f'{component}_material_count'] = material_count + 1
                        st.rerun()  # Ändern Sie dies von st.experimental_rerun()

                with accessory_tab:
                    accessory_count = st.session_state.get(f'{component}_accessory_count', 1)
                    for i in range(accessory_count):
                        # ... (vorheriger Code bleibt unverändert)
                        with col4:
                            if st.button('X', key=f'{component}_remove_accessory_{i}'):
                                if f'{component}_accessory_{i}' in st.session_state:
                                    del st.session_state[f'{component}_accessory_{i}']
                                if f'{component}_accessory_amount_{i}' in st.session_state:
                                    del st.session_state[f'{component}_accessory_amount_{i}']
                                st.session_state[f'{component}_accessory_count'] = max(1, accessory_count - 1)
                                st.rerun()  # Ändern Sie dies von st.experimental_rerun()
                    if st.button('Zubehör hinzufügen', key=f'{component}_add_accessory'):
                        st.session_state[f'{component}_accessory_count'] = accessory_count + 1
                        st.rerun()  # Ändern Sie dies von st.experimental_rerun()

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
                                total_cost += accessory_cost
                                component_costs[component]['Zubehör'][accessory] = {'amount': amount, 'cost': accessory_cost}
                                st.markdown(f'<div style="text-align: right;">{accessory_cost:.2f} €</div>', unsafe_allow_html=True)
                        with col4:
                            if st.button('X', key=f'{component}_remove_accessory_{i}'):
                                if f'{component}_accessory_{i}' in st.session_state:
                                    del st.session_state[f'{component}_accessory_{i}']
                                if f'{component}_accessory_amount_{i}' in st.session_state:
                                    del st.session_state[f'{component}_accessory_amount_{i}']
                                st.session_state[f'{component}_accessory_count'] = max(1, accessory_count - 1)
                                st.experimental_rerun()
                    if st.button('Zubehör hinzufügen', key=f'{component}_add_accessory'):
                        st.session_state[f'{component}_accessory_count'] = accessory_count + 1
                        st.experimental_rerun()

                with cost_breakdown_tab:
                    st.subheader('Kostenaufschlüsselung')
                    st.write('Materialien:')
                    for material, data in component_costs[component]['Materialien'].items():
                        st.write(f'- {material}: {data["cost"]:.2f} €')
                    st.write('Zubehör:')
                    for accessory, data in component_costs[component]['Zubehör'].items():
                        st.write(f'- {accessory}: {data["cost"]:.2f} €')
                    st.write(f'Arbeitskosten: {component_costs[component]["Arbeitskosten"]:.2f} €')
                    component_total = sum(data["cost"] for data in component_costs[component]['Materialien'].values()) + \
                                    sum(data["cost"] for data in component_costs[component]['Zubehör'].values()) + \
                                    component_costs[component]['Arbeitskosten']
                    st.write(f'Gesamtkosten für {component}: {component_total:.2f} €')    

        st.divider()
        st.subheader('Gesamtübersicht')
        cost_data, total_material_cost, total_accessory_cost, total_labor_cost, total_cost, profit_amount, final_price = create_cost_overview(components, component_costs, materials_db, accessories_db, hourly_rate, overhead_costs, consultation_costs, profit_margin)

        df = pd.DataFrame(cost_data)
        st.table(df)

        costs = [total_material_cost, total_accessory_cost, total_labor_cost, overhead_costs, consultation_costs]
        labels = ['Materialien', 'Zubehör', 'Arbeitskosten', 'Gemeinkosten', 'Beratung']
        create_pie_chart(costs, labels)

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
                    
                    save_outfit(outfit_name, components, 
                                {c: outfit_components[c]['materials'] for c in components},
                                {c: outfit_components[c]['accessories'] for c in components},
                                {c: outfit_components[c]['work_hours'] for c in components},
                                hourly_rate, overhead_costs, consultation_costs,
                                total_material_cost, total_accessory_cost, total_labor_cost,
                                total_cost, profit_margin, profit_amount, final_price, category)
                st.success(f'Outfit "{outfit_name}" erfolgreich gespeichert!')

    with tab2:
        st.subheader('Materialien verwalten')
        
        with st.form(key='add_material_form'):
            material_name = st.text_input('Materialname')
            average_price = st.number_input('Durchschnittspreis (€)', min_value=0.0, step=0.01)
            waste_percentage = st.number_input('Abfallprozentsatz (%)', min_value=0.0, step=0.1)
            submit_button = st.form_submit_button(label='Material hinzufügen')
            
            if submit_button:
                add_material(material_name, average_price, waste_percentage)
        
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
                    delete_material(row['material'])
                    st.experimental_rerun()
            if new_price != row['average_price'] or new_waste != row['waste_percentage']:
                materials_db.at[index, 'average_price'] = new_price
                materials_db.at[index, 'waste_percentage'] = new_waste
                update_data(materials_db, 'materials')

    with tab3:
        st.subheader('Zubehör verwalten')
        
        with st.form(key='add_accessory_form'):
            accessory_name = st.text_input('Zubehörname')
            price = st.number_input('Preis (€)', min_value=0.0, step=0.01)
            submit_button = st.form_submit_button(label='Zubehör hinzufügen')
            
            if submit_button:
                add_accessory(accessory_name, price)
        
        st.write("Vorhandenes Zubehör:")
        for index, row in accessories_db.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(row['accessory'])
            with col2:
                new_price = st.number_input('Preis (€)', value=float(row['price']), key=f"accessory_price_{index}", step=0.01)
            with col3:
                if st.button('Löschen', key=f"delete_accessory_{index}"):
                    delete_accessory(row['accessory'])
                    st.experimental_rerun()
            if new_price != row['price']:
                accessories_db.at[index, 'price'] = new_price
                update_data(accessories_db, 'accessories')

    with tab4:
        st.subheader('Gespeicherte Outfits')
        display_saved_outfits(hourly_rate, overhead_costs, materials_db, accessories_db, profit_margin, consultation_hours)

    with tab5:
        analyze_outfits()

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

