import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
import json
import os
import shutil
from datetime import datetime

supabase_url = "https://qormgjgpisbzyegipbiq.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFvcm1namdwaXNienllZ2lwYmlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjkxODY2NjMsImV4cCI6MjA0NDc2MjY2M30.JB7xuS8R8nBShuTYm5LmZifHR7SpsEYxcVOaag8uRKI"
supabase: Client = create_client(supabase_url, supabase_key)

def get_db_connection():
    return supabase

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
    for index, row in data.iterrows():
        supabase.table(table_name).upsert(row.to_dict()).execute()
    return True

def save_data(data, table_name):
    updated = update_data(data, table_name)
    if updated:
        st.success(f'Daten in {table_name} aktualisiert!')
    else:
        st.error(f'Fehler beim Aktualisieren der Daten in {table_name}.')

def save_outfit(name, components, materials, accessories, work_hours, hourly_rate, overhead_costs, total_cost):
    supabase.table('saved_outfits').insert({
        'name': name,
        'components': json.dumps(components),
        'materials': json.dumps(materials),
        'accessories': json.dumps(accessories),
        'work_hours': json.dumps(work_hours),
        'hourly_rate': hourly_rate,
        'overhead_costs': overhead_costs,
        'total_cost': total_cost
    }).execute()

def delete_outfit(id):
    supabase.table('saved_outfits').delete().eq('id', id).execute()

def delete_material(material_name):
    supabase.table('materials').delete().eq('material', material_name).execute()
    st.success(f"Material '{material_name}' erfolgreich gelöscht!")

def delete_accessory(accessory_name):
    supabase.table('accessories').delete().eq('accessory', accessory_name).execute()
    st.success(f"Zubehör '{accessory_name}' erfolgreich gelöscht!")

def format_currency(value):
    return f"{value:.2f} €"

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
            if isinstance(data, dict):
                amount = data.get('amount', 0)
                cost = data.get('cost', 0)
            else:
                amount = data
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
            if isinstance(data, dict):
                amount = data.get('amount', 0)
                cost = data.get('cost', 0)
            else:
                amount = data
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

def backup_database():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f'outfit_calculator_backup_{current_time}.db'
    shutil.copy2('outfit_calculator.db', backup_filename)
    st.success(f'Datenbank-Backup erstellt: {backup_filename}')

def display_saved_outfits(current_hourly_rate, current_overhead_costs, current_materials_db, current_accessories_db):
    saved_outfits = load_data('saved_outfits')
    if saved_outfits.empty:
        st.write("Keine Outfits gespeichert.")
    else:
        for index, outfit in saved_outfits.iterrows():
            with st.expander(f"{outfit['name']} (ID: {outfit['id']})"):
                try:
                    components = json.loads(outfit['components'])
                    materials = json.loads(outfit['materials'])
                    accessories = json.loads(outfit['accessories'])
                    work_hours = json.loads(outfit['work_hours'])
                    
                    component_costs = {
                        component: {
                            'Materialien': materials.get(component, {}),
                            'Zubehör': accessories.get(component, {}),
                            'Arbeitskosten': work_hours.get(component, 0) * current_hourly_rate
                        } for component in components
                    }
                    
                    cost_data, total_material_cost, total_accessory_cost, total_labor_cost, total_cost, profit_amount, final_price = create_cost_overview(
                        components, component_costs, current_materials_db, current_accessories_db,
                        current_hourly_rate, current_overhead_costs, outfit['hourly_rate'] * 2,
                        20
                    )
                    
                    if cost_data:
                        df = pd.DataFrame(cost_data)
                        st.table(df)
                        
                        costs = [total_material_cost, total_accessory_cost, total_labor_cost, current_overhead_costs, outfit['hourly_rate'] * 2]
                        labels = ['Materialien', 'Zubehör', 'Arbeitskosten', 'Gemeinkosten', 'Beratung']
                        create_pie_chart(costs, labels)
                    else:
                        st.warning("Keine Kostendaten für dieses Outfit verfügbar.")
                    
                except Exception as e:
                    st.error(f"Fehler beim Laden des Outfits: {str(e)}")
                
                if st.button('Outfit löschen', key=f"delete_{outfit['id']}"):
                    delete_outfit(outfit['id'])
                    st.success(f"Outfit '{outfit['name']}' wurde gelöscht. Bitte laden Sie die Seite neu, um die Änderungen zu sehen.")

def add_material(material_name, average_price, waste_percentage):
    try:
        supabase.table('materials').insert({
            'material': material_name,
            'average_price': average_price,
            'waste_percentage': waste_percentage
        }).execute()
        st.success(f"Material '{material_name}' erfolgreich hinzugefügt!")
    except Exception as e:
        st.error(f"Fehler beim Hinzufügen des Materials: {str(e)}")

def add_accessory(accessory_name, price):
    try:
        supabase.table('accessories').insert({
            'accessory': accessory_name,
            'price': price
        }).execute()
        st.success(f"Zubehör '{accessory_name}' erfolgreich hinzugefügt!")
    except Exception as e:
        st.error(f"Fehler beim Hinzufügen des Zubehörs: {str(e)}")

materials_db = load_data('materials')
accessories_db = load_data('accessories')

st.title('Outfit-Preis-Kalkulator')

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Kalkulator", "Materialien verwalten", "Zubehör verwalten", "Gespeicherte Outfits", "Hilfe"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        hourly_rate = st.number_input('Stundensatz (€)', min_value=0.0, value=40.0, step=0.5)
        fixed_costs = st.number_input('Fixkosten (€)', min_value=0.0, value=1064.0, step=10.0)
    with col2:
        outfits_per_month = st.number_input('Outfits pro Monat', min_value=1, value=3, step=1)
        consultation_hours = st.number_input('Beratungsstunden', min_value=0.0, value=2.0, step=0.5)

    profit_margin = st.slider('Gewinnmarge (%)', min_value=0, max_value=100, value=20, step=5)

    overhead_costs = fixed_costs / outfits_per_month
    consultation_costs = consultation_hours * hourly_rate
    st.write(f'Gemeinkosten pro Outfit: {overhead_costs:.2f} €')
    st.write(f'Beratungskosten: {consultation_costs:.2f} €')
    st.divider()

    all_possible_components = ['Kleid', 'Jacke', 'Oberteil', 'Hose', 'Rock', 'Overall']

    st.subheader('Outfit-Komponenten')
    components = [component for component in all_possible_components if st.checkbox(component)]

    total_cost = overhead_costs + consultation_costs

    component_costs = {component: {'Materialien': {}, 'Zubehör': {}, 'Arbeitskosten': 0} for component in all_possible_components}

    for component in components:
        with st.expander(f'{component} Details', expanded=True):
            work_hours = st.number_input(f'Arbeitszeit für {component} (Stunden)', min_value=0.0, key=f'{component}_hours', step=0.5)
            labor_cost = work_hours * hourly_rate
            total_cost += labor_cost
            component_costs[component]['Arbeitskosten'] = labor_cost
            st.write(f'Arbeitskosten: {labor_cost:.2f} €')
            
            material_tab, accessory_tab, cost_breakdown_tab = st.tabs(["Materialien", "Zubehör", "Kostenaufschlüsselung"])
            
            with material_tab:
                material_count = st.session_state.get(f'{component}_material_count', 1)
                for i in range(material_count):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        material = st.selectbox('Material', options=[''] + materials_db['material'].tolist(), key=f'{component}_material_{i}')
                    with col2:
                        amount = st.number_input('Menge (m)', min_value=0.0, key=f'{component}_material_amount_{i}', step=0.5)
                    with col3:
                        if material:
                            material_data = materials_db[materials_db['material'] == material].iloc[0]
                            material_price = float(material_data['average_price'])
                            material_waste = float(material_data['waste_percentage']) / 100
                            material_cost = amount * material_price * (1 + material_waste)
                            total_cost += material_cost
                            component_costs[component]['Materialien'][material] = amount
                            st.markdown(f'<div style="text-align: right;">{material_cost:.2f} €</div>', unsafe_allow_html=True)
                    with col4:
                        if st.button('X', key=f'{component}_remove_material_{i}'):
                            if f'{component}_material_{i}' in st.session_state:
                                del st.session_state[f'{component}_material_{i}']
                            if f'{component}_material_amount_{i}' in st.session_state:
                                del st.session_state[f'{component}_material_amount_{i}']
                            st.session_state[f'{component}_material_count'] = max(1, material_count - 1)
                if st.button('Material hinzufügen', key=f'{component}_add_material'):
                    st.session_state[f'{component}_material_count'] = material_count + 1

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
                            component_costs[component]['Zubehör'][accessory] = amount
                            st.markdown(f'<div style="text-align: right;">{accessory_cost:.2f} €</div>', unsafe_allow_html=True)
                    with col4:
                        if st.button('X', key=f'{component}_remove_accessory_{i}'):
                            if f'{component}_accessory_{i}' in st.session_state:
                                del st.session_state[f'{component}_accessory_{i}']
                            if f'{component}_accessory_amount_{i}' in st.session_state:
                                del st.session_state[f'{component}_accessory_amount_{i}']
                            st.session_state[f'{component}_accessory_count'] = max(1, accessory_count - 1)
                if st.button('Zubehör hinzufügen', key=f'{component}_add_accessory'):
                    st.session_state[f'{component}_accessory_count'] = accessory_count + 1

            with cost_breakdown_tab:
                st.subheader('Kostenaufschlüsselung')
                st.write('Materialien:')
                for material, amount in component_costs[component]['Materialien'].items():
                    material_data = materials_db[materials_db['material'] == material].iloc[0]
                    material_price = float(material_data['average_price'])
                    material_waste = float(material_data['waste_percentage']) / 100
                    material_cost = amount * material_price * (1 + material_waste)
                    st.write(f'- {material}: {material_cost:.2f} €')
                st.write('Zubehör:')
                for accessory, amount in component_costs[component]['Zubehör'].items():
                    accessory_data = accessories_db[accessories_db['accessory'] == accessory].iloc[0]
                    accessory_price = float(accessory_data['price'])
                    accessory_cost = amount * accessory_price
                    st.write(f'- {accessory}: {accessory_cost:.2f} €')
                st.write(f'Arbeitskosten: {component_costs[component]["Arbeitskosten"]:.2f} €')
                component_total = sum(materials_db[materials_db['material'] == m]['average_price'].iloc[0] * amount * (1 + materials_db[materials_db['material'] == m]['waste_percentage'].iloc[0] / 100) for m, amount in component_costs[component]['Materialien'].items()) + \
                                sum(accessories_db[accessories_db['accessory'] == a]['price'].iloc[0] * amount for a, amount in component_costs[component]['Zubehör'].items()) + \
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
    if st.button('Outfit speichern') and outfit_name:
        outfit_components = {component: {
            'materials': {m: {'amount': amount, 'cost': materials_db[materials_db['material'] == m]['average_price'].iloc[0] * amount * (1 + materials_db[materials_db['material'] == m]['waste_percentage'].iloc[0] / 100)} for m, amount in component_costs[component]['Materialien'].items()},
            'accessories': {a: {'amount': amount, 'cost': accessories_db[accessories_db['accessory'] == a]['price'].iloc[0] * amount} for a, amount in component_costs[component]['Zubehör'].items()},
            'work_hours': component_costs[component]['Arbeitskosten'] / hourly_rate
        } for component in components}
        
        save_outfit(outfit_name, components, 
                    {c: outfit_components[c]['materials'] for c in components},
                    {c: outfit_components[c]['accessories'] for c in components},
                    {c: outfit_components[c]['work_hours'] for c in components},
                    hourly_rate, overhead_costs, total_cost)
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
    display_saved_outfits(hourly_rate, overhead_costs, materials_db, accessories_db)

with tab5:
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
    - Klicken Sie auf 'Änderungen speichern', um Ihre Änderungen zu sichern.

    3. Im 'Zubehör verwalten' Tab:
    - Fügen Sie neues Zubehör hinzu, bearbeiten oder löschen Sie bestehendes.
    - Klicken Sie auf 'Änderungen speichern', um Ihre Änderungen zu sichern.

    4. Im 'Gespeicherte Outfits' Tab:
    - Sehen Sie sich Ihre gespeicherten Outfits an.
    - Die Preise werden automatisch basierend auf den aktuellen Parametern aktualisiert.

    Alle Änderungen werden automatisch in der Datenbank gespeichert und stehen allen Benutzern zur Verfügung.

    Bei Fragen oder Problemen wenden Sie sich bitte an den Support.
    """)