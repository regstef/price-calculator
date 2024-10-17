import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import json
import os

def get_db_connection():
    conn = sqlite3.connect('outfit_calculator.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS materials
                 (id INTEGER PRIMARY KEY, 
                  material TEXT, 
                  average_price REAL, 
                  waste_percentage REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS accessories
                 (id INTEGER PRIMARY KEY, 
                  accessory TEXT, 
                  price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS saved_outfits
                 (id INTEGER PRIMARY KEY,
                  name TEXT,
                  components TEXT,
                  materials TEXT,
                  accessories TEXT,
                  work_hours TEXT,
                  hourly_rate REAL,
                  overhead_costs REAL,
                  total_cost REAL)''')
    conn.commit()
    conn.close()

def update_db_structure():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(saved_outfits)")
    columns = [column[1] for column in c.fetchall()]
    
    required_columns = ['hourly_rate', 'overhead_costs', 'total_cost']
    for column in required_columns:
        if column not in columns:
            c.execute(f"ALTER TABLE saved_outfits ADD COLUMN {column} REAL")
    
    conn.commit()
    conn.close()

update_db_structure()

def load_data(table_name):
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def save_data(data, table_name):
    conn = get_db_connection()
    data.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    st.success(f'Daten in {table_name} gespeichert!')

def save_outfit(name, components, materials, accessories, work_hours, hourly_rate, overhead_costs, total_cost):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO saved_outfits 
                 (name, components, materials, accessories, work_hours, hourly_rate, overhead_costs, total_cost)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
              (name, json.dumps(components), json.dumps(materials), 
               json.dumps(accessories), json.dumps(work_hours), hourly_rate, overhead_costs, total_cost))
    conn.commit()
    conn.close()

def delete_outfit(id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''DELETE FROM saved_outfits WHERE id = ?''', (id,))
    conn.commit()
    conn.close()

def format_currency(value):
    return f"{value:.2f} €"

def create_cost_overview(components, component_costs, materials_db, accessories_db, hourly_rate, overhead_costs, consultation_costs, profit_margin):
    cost_data = []
    total_material_cost = 0
    total_accessory_cost = 0
    total_labor_cost = 0

    # Materialkosten
    for component in components:
        for material, data in component_costs[component]['Materialien'].items():
            if isinstance(data, dict):
                amount = data.get('amount', 0)
                cost = data.get('cost', 0)
            else:
                amount = data
                material_data = materials_db[materials_db['material'] == material].iloc[0]
                material_price = float(material_data['average_price'])
                material_waste = float(material_data['waste_percentage']) / 100
                cost = amount * material_price * (1 + material_waste)
            
            total_material_cost += cost
            cost_data.append({
                'Kategorie': 'Materialkosten',
                'Komponente': component,
                'Beschreibung': f"{material}: {amount} m",
                'Betrag (€)': format_currency(cost)
            })

    # Gesamtmaterialkosten
    cost_data.append({
        'Kategorie': 'Gesamtmaterialkosten',
        'Komponente': '',
        'Beschreibung': '',
        'Betrag (€)': format_currency(total_material_cost)
    })

    # Zubehörkosten
    for component in components:
        for accessory, data in component_costs[component]['Zubehör'].items():
            if isinstance(data, dict):
                amount = data.get('amount', 0)
                cost = data.get('cost', 0)
            else:
                amount = data
                accessory_data = accessories_db[accessories_db['accessory'] == accessory].iloc[0]
                accessory_price = float(accessory_data['price'])
                cost = amount * accessory_price
            
            total_accessory_cost += cost
            cost_data.append({
                'Kategorie': 'Zubehörkosten',
                'Komponente': component,
                'Beschreibung': f"{accessory}: {amount} Stück",
                'Betrag (€)': format_currency(cost)
            })

    # Gesamtzubehörkosten
    cost_data.append({
        'Kategorie': 'Gesamtzubehörkosten',
        'Komponente': '',
        'Beschreibung': '',
        'Betrag (€)': format_currency(total_accessory_cost)
    })

    # Arbeitskosten
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

    # Gesamtarbeitskosten
    cost_data.append({
        'Kategorie': 'Gesamtarbeitskosten',
        'Komponente': '',
        'Beschreibung': '',
        'Betrag (€)': format_currency(total_labor_cost)
    })

    # Zusätzliche Kosten
    cost_data.extend([
        {'Kategorie': 'Zusätzliche Kosten', 'Komponente': '-', 'Beschreibung': 'Gemeinkosten', 'Betrag (€)': format_currency(overhead_costs)},
        {'Kategorie': 'Zusätzliche Kosten', 'Komponente': '-', 'Beschreibung': 'Beratungskosten', 'Betrag (€)': format_currency(consultation_costs)}
    ])

    # Gesamtkosten berechnen
    total_cost = total_material_cost + total_accessory_cost + total_labor_cost + overhead_costs + consultation_costs

    # Gewinn und Verkaufspreis
    profit_amount = total_cost * (profit_margin / 100)
    final_price = total_cost + profit_amount

    # Gesamtübersicht hinzufügen
    cost_data.extend([
        {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Gesamtproduktionskosten', 'Betrag (€)': format_currency(total_cost)},
        {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': f'Gewinnbetrag ({profit_margin}%)', 'Betrag (€)': format_currency(profit_amount)},
        {'Kategorie': 'Gesamtübersicht', 'Komponente': '-', 'Beschreibung': 'Empfohlener Verkaufspreis', 'Betrag (€)': format_currency(final_price)}
    ])

    return cost_data, [total_material_cost, total_accessory_cost, total_labor_cost, overhead_costs, consultation_costs]

init_db()

materials_db = load_data('materials')
accessories_db = load_data('accessories')

if materials_db.empty:
    materials_db = pd.DataFrame({
        'material': ['Baumwolle', 'Seide', 'Leinen'],
        'average_price': [10, 30, 20],
        'waste_percentage': [10, 15, 12]
    })
    save_data(materials_db, 'materials')

if accessories_db.empty:
    accessories_db = pd.DataFrame({
        'accessory': ['Knöpfe', 'Reißverschluss', 'Gürtel'],
        'price': [0.5, 2, 5]
    })
    save_data(accessories_db, 'accessories')

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
                            del st.session_state[f'{component}_material_{i}']
                            del st.session_state[f'{component}_material_amount_{i}']
                            st.session_state[f'{component}_material_count'] = material_count - 1
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
                            total_cost += accessory_cost
                            component_costs[component]['Zubehör'][accessory] = amount
                            st.markdown(f'<div style="text-align: right;">{accessory_cost:.2f} €</div>', unsafe_allow_html=True)
                    with col4:
                        if st.button('X', key=f'{component}_remove_accessory_{i}'):
                            del st.session_state[f'{component}_accessory_{i}']
                            del st.session_state[f'{component}_accessory_amount_{i}']
                            st.session_state[f'{component}_accessory_count'] = accessory_count - 1
                            st.rerun()
                if st.button('Zubehör hinzufügen', key=f'{component}_add_accessory'):
                    st.session_state[f'{component}_accessory_count'] = accessory_count + 1
                    st.rerun()

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
    cost_data, costs = create_cost_overview(components, component_costs, materials_db, accessories_db, hourly_rate, overhead_costs, consultation_costs, profit_margin)

    # Erstellen und Anzeigen der Tabelle
    df = pd.DataFrame(cost_data)
    st.table(df)

    # Kuchendiagramm
    fig, ax = plt.subplots()
    labels = ['Materialien', 'Zubehör', 'Arbeitskosten', 'Gemeinkosten', 'Beratung']
    ax.pie(costs, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)

    st.divider()
    # Outfit speichern
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
    
    edited_materials = st.data_editor(materials_db, num_rows="dynamic")
    
    if st.button('Änderungen an Materialien speichern'):
        save_data(edited_materials, 'materials')
        materials_db = edited_materials

with tab3:
    st.subheader('Zubehör verwalten')
    
    edited_accessories = st.data_editor(accessories_db, num_rows="dynamic")
    
    if st.button('Änderungen an Zubehör speichern'):
        save_data(edited_accessories, 'accessories')
        accessories_db = edited_accessories

with tab4:
    st.subheader('Gespeicherte Outfits')
    
    def display_saved_outfits(current_hourly_rate, current_overhead_costs, current_materials_db, current_accessories_db):
        saved_outfits = load_data('saved_outfits')
        if saved_outfits.empty:
            st.write("Keine Outfits gespeichert.")
        else:
            for index, outfit in saved_outfits.iterrows():
                with st.expander(f"{outfit['name']} (ID: {outfit['id']})"):
                    components = json.loads(outfit['components'])
                    materials = json.loads(outfit['materials'])
                    accessories = json.loads(outfit['accessories'])
                    work_hours = json.loads(outfit['work_hours'])
                    
                    # Rekonstruktion der component_costs Struktur
                    component_costs = {
                        component: {
                            'Materialien': materials[component],
                            'Zubehör': accessories[component],
                            'Arbeitskosten': work_hours[component] * current_hourly_rate
                        } for component in components
                    }
                    
                    # Verwendung der create_cost_overview Funktion
                    cost_data, costs = create_cost_overview(
                        components, component_costs, current_materials_db, current_accessories_db,
                        current_hourly_rate, current_overhead_costs, outfit['hourly_rate'] * 2,  # Annahme: 2 Beratungsstunden
                        20  # Standardmäßige Gewinnmarge von 20%
                    )
                    
                    # Anzeigen der Tabelle
                    df = pd.DataFrame(cost_data)
                    st.table(df)
                    
                    # Überprüfen und Behandeln von NaN-Werten
                    costs = [0 if pd.isna(cost) else cost for cost in costs]
                    
                    # Nur das Kuchendiagramm erstellen, wenn wir gültige Daten haben
                    if sum(costs) > 0:
                        # Kuchendiagramm
                        fig, ax = plt.subplots()
                        labels = ['Materialien', 'Zubehör', 'Arbeitskosten', 'Gemeinkosten', 'Beratung']
                        ax.pie(costs, labels=labels, autopct='%1.1f%%', startangle=90)
                        ax.axis('equal')
                        st.pyplot(fig)
                    else:
                        st.warning("Nicht genügend Daten für ein Kuchendiagramm vorhanden.")
                    
                    # Löschen-Button
                    if st.button('Outfit löschen', key=f"delete_{outfit['id']}"):
                        delete_outfit(outfit['id'])
                        st.success(f"Outfit '{outfit['name']}' wurde gelöscht. Bitte laden Sie die Seite neu, um die Änderungen zu sehen.")

    # Aufruf der Funktion
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

if __name__ == "__main__":
    update_db_structure()