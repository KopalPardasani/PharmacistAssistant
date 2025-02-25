import gradio as gr
import pytesseract
import spacy
import json
import pandas as pd
import re
from fuzzywuzzy import process
from PIL import Image

# Load SpaCy's pretrained NER model (used to extract medicine names)
nlp = spacy.load("en_core_web_sm")

# Sample medicine inventory (Can be replaced with a real database)
inventory_data = {
    # Painkillers & Fever
    "Paracetamol": 500, "Ibuprofen": 400, "Aspirin": 300, "Diclofenac": 250, "Naproxen": 200,
    "Tramadol": 150, "Celecoxib": 180, "Codeine": 120, "Morphine": 80, "Fentanyl": 60,
    
    # Antibiotics
    "Amoxicillin": 300, "Azithromycin": 250, "Ciprofloxacin": 220, "Doxycycline": 180, "Clarithromycin": 200,
    "Metronidazole": 190, "Rifampicin": 160, "Cephalexin": 140, "Erythromycin": 170, "Vancomycin": 100,
    
    # Antidiabetics
    "Metformin": 350, "Glimepiride": 200, "Sitagliptin": 180, "Pioglitazone": 150, "Insulin": 300,
    "Liraglutide": 130, "Canagliflozin": 140, "Dapagliflozin": 120, "Acarbose": 110, "Gliclazide": 100,
    
    # Blood Pressure & Heart
    "Losartan": 400, "Amlodipine": 380, "Metoprolol": 350, "Enalapril": 340, "Ramipril": 300,
    "Atenolol": 290, "Carvedilol": 270, "Hydrochlorothiazide": 260, "Verapamil": 250, "Furosemide": 220,
    
    # Cholesterol
    "Atorvastatin": 450, "Simvastatin": 400, "Rosuvastatin": 380, "Pravastatin": 360, "Ezetimibe": 300,
    
    # Mental Health & CNS
    "Sertraline": 320, "Fluoxetine": 310, "Citalopram": 290, "Escitalopram": 280, "Venlafaxine": 270,
    "Duloxetine": 260, "Bupropion": 250, "Risperidone": 240, "Olanzapine": 230, "Quetiapine": 220,
    
    # Asthma & COPD
    "Salbutamol": 500, "Montelukast": 480, "Budesonide": 460, "Tiotropium": 440, "Ipratropium": 420,
    "Fluticasone": 400, "Mometasone": 380, "Theophylline": 360, "Prednisone": 340, "Dexamethasone": 320,
    
    # Stomach & Digestion
    "Omeprazole": 450, "Esomeprazole": 430, "Pantoprazole": 420, "Ranitidine": 400, "Famotidine": 380,
    "Domperidone": 350, "Metoclopramide": 320, "Loperamide": 300, "Ondansetron": 280, "Sucralfate": 260,
    
    # Thyroid & Hormones
    "Levothyroxine": 500, "Liothyronine": 480, "Methimazole": 450, "Propylthiouracil": 430, "Hydrocortisone": 400,
    
    # Immunosuppressants
    "Cyclosporine": 300, "Tacrolimus": 280, "Azathioprine": 260, "Mycophenolate": 250, "Methotrexate": 230,
    
    # Blood Thinners & Anti-Clotting
    "Warfarin": 400, "Clopidogrel": 380, "Dabigatran": 360, "Apixaban": 340, "Rivaroxaban": 320,
    
    # Pain Management & Neuropathy
    "Gabapentin": 500, "Pregabalin": 480, "Amitriptyline": 450, "Nortriptyline": 430, "Duloxetine": 410,
    
    # Anti-Allergy
    "Cetirizine": 500, "Loratadine": 480, "Fexofenadine": 460, "Diphenhydramine": 440, "Chlorpheniramine": 420,
    
    # Anti-Seizure
    "Levetiracetam": 500, "Valproic Acid": 480, "Carbamazepine": 460, "Lamotrigine": 440, "Phenytoin": 420,
    
    # Eye Care
    "Latanoprost": 500, "Timolol": 480, "Brimonidine": 460, "Dorzolamide": 440, "Bimatoprost": 420
}

inventory_df = pd.DataFrame(list(inventory_data.items()), columns=["Medicine_Name", "Stock"])

# Function 1: OCR - Extract text from prescription
def extract_text(image):
    text = pytesseract.image_to_string(image)
    return text.strip()

# Function 2: Extract medicine names using NER
def extract_medicines(text):
    doc = nlp(text)
    medicines = [ent.text for ent in doc.ents if ent.label_ == "ORG"]  # Assuming medicine names appear as ORG
    return medicines if medicines else ["No medicines detected"]

# Function 3: Match extracted medicines with inventory (Fixed NoneType error)
def match_inventory(medicines):
    matched = {}
    for med in medicines:
        result = process.extractOne(med, inventory_df["Medicine_Name"].tolist(), score_cutoff=80)
        if result:  # Check if a match is found
            best_match, _ = result
            stock = inventory_df[inventory_df["Medicine_Name"] == best_match]["Stock"].values[0]
            matched[best_match] = f"In stock: {stock}"
        else:
            matched[med] = "Not Available"
    return matched

# Function 4: Extract dosage and frequency from text
def extract_dosage_frequency(text):
    dosage_pattern = r"(\d+\s?(mg|ml|g|tablets|capsules))"
    frequency_pattern = r"(once|twice|thrice|daily|weekly|morning|night|every\s\d+\shours)"
    
    dosages = re.findall(dosage_pattern, text)
    frequencies = re.findall(frequency_pattern, text)
    
    return {
        "Dosage": [d[0] for d in dosages] if dosages else ["Not specified"],
        "Frequency": frequencies if frequencies else ["Not specified"]
    }

# Function 5: Generate final structured order
def generate_order(image):
    text = extract_text(image)
    medicines = extract_medicines(text)
    matched_medicines = match_inventory(medicines)
    dosage_frequency = extract_dosage_frequency(text)
    
    order = {
        "Extracted Prescription Text": text,
        "Identified Medicines": matched_medicines,
        "Dosage & Frequency": dosage_frequency
    }
    
    return json.dumps(order, indent=4)

# Gradio UI
interface = gr.Interface(
    fn=generate_order,
    inputs=gr.Image(type="pil"),
    outputs="text",
    title="Pharmacist’s Assistant",
    description="Upload a handwritten prescription image. The system extracts medicine names, checks availability, and generates an order."
)

if __name__ == "__main__":
    interface.launch()

