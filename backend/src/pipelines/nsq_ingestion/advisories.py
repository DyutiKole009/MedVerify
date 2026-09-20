"""
Qualitative regulatory advisories, counterfeit visual cues, clinical monographs,
and public health directives for Amazon Bedrock Knowledge Base vector indexing.
Contains unstructured prose that cannot be modeled as tabular database records.
"""
from typing import Dict, List

UNSTRUCTURED_ADVISORIES: List[Dict[str, str]] = [
    {
        "filename": "CDSCO_Advisory_Anti_Counterfeit_Packaging_Protocols.md",
        "title": "CDSCO Public Advisory: Anti-Counterfeit Packaging Detection Protocols & Visual Inspection Standards",
        "content": """# Central Drugs Standard Control Organisation (CDSCO)
## Directorate General of Health Services, Ministry of Health & Family Welfare, Government of India
### Regulatory Guidance: Identification of Spurious Drugs via Secondary and Primary Packaging Anomalies

#### 1. Background & Scope
Spurious, adulterated, and falsely labelled medicines pose severe threats to public health. Under Section 17-B of the Drugs and Cosmetics Act, 1940, a drug is deemed spurious if it is manufactured under a name belonging to another drug, if it is an imitation of another drug, or if the manufacturer specified on the label is fictitious. This document provides visual inspection guidance for drug inspectors, registered pharmacists, and consumers.

#### 2. Physical & Packaging Discrepancies Commonly Observed in Counterfeit Formulations
1. **Foil Substrate & Blister Integrity:**
   - Genuine blister packaging typically utilizes high-tensile 250-micron PVC/PVDC or cold-form aluminium (Alu-Alu) foil. Counterfeiters frequently employ substandard 150-micron brittle recycled foil which tears easily upon finger pressure.
   - Pinhole leaks or non-uniform knurling on heat-sealed borders indicate non-validated sealing machinery common in clandestine manufacturing setups.
2. **Typography, Kerning & Color Register:**
   - Brand name fonts must match official pharmacopoeial registrations. Counterfeits frequently display irregular character spacing, slight font weight variations (e.g. bolded letters where regular is standard), or smudged micro-lettering.
   - Misspellings in manufacturer addresses, pin codes, or inactive ingredient declarations (e.g. spelling 'Excipients' as 'Exepients') are primary indicators of counterfeit stock.
3. **Security Holograms & Optical Variable Inks (OVI):**
   - High-risk drugs (such as broad-spectrum cephalosporins, oncology formulations, and high-potency analgesics) incorporate dual-channel kinetic holograms. Counterfeit holograms are usually static foil prints that do not exhibit color shifting or 90-degree depth transitions under ambient light.
   - Barcode and 2D Data Matrix QR codes must decode into GS1 standard Global Trade Item Number (GTIN), batch number, expiry date, and serial number. Static or unreadable QR codes should immediately be quarantined.
4. **Tablet & Capsule Morphology:**
   - In genuine production, tablet thickness and diameter maintain tight tolerances (+/-2%). Substandard batches often exhibit edge chipping, capping, mottling (uneven color distribution), or variable debossing depth.
   - Hard gelatin capsules should have secure locking rings (Snap-Fit). Counterfeit capsules frequently pull apart with negligible force or contain variable fill powder volume.

#### 3. High-Risk Drug Categories Under CDSCO Surveillance
Formulations most frequently counterfeited or found Not of Standard Quality (NSQ) include:
- Paracetamol & Diclofenac fixed-dose combinations.
- Gastrointestinal formulations: Pantoprazole, Omeprazole, and Rabeprazole Sodium capsules.
- Broad-spectrum antibiotics: Amoxicillin-Clavulanic acid, Azithromycin, Ciprofloxacin, and Cefixime.
- Chronic therapy medicines: Amlodipine, Metformin prolonged-release, and Telmisartan.
- Essential injections: Sterile Sodium Chloride 0.9%, Compound Sodium Lactate, and Dextrose infusions.
"""
    },
    {
        "filename": "CDSCO_Warning_Bulletin_Transit_Theft_Supply_Chain.md",
        "title": "CDSCO Regulatory Alert: Supply Chain Security & Transit Theft Interception Directives",
        "content": """# Central Drugs Standard Control Organisation (CDSCO)
## Ministry of Health & Family Welfare, Government of India
### Enforcement Alert: Security of Temperature-Sensitive Pharmaceuticals and Cargo Interception

#### 1. Official Enforcement Notice
CDSCO periodically issues cargo and warehouse diversion alerts when legitimate pharmaceutical consignments are compromised during distribution or transit. A prominent case involved the transit theft of temperature-sensitive medications (including specialized insulin formulations and GLP-1 analogues of M/s Novo Nordisk India).

#### 2. Clinical & Biological Risks of Diverted Medicines
1. **Cold-Chain Breakdown & Protein Denaturation:**
   - Biological products, including insulins, monoclonal antibodies, and vaccines, require continuous refrigeration between 2 deg C and 8 deg C. Once diverted or stolen, these medicines are routinely held in uncontrolled non-refrigerated conditions (often exceeding 35 deg C to 40 deg C in transit hubs).
   - Thermal degradation causes irreversible protein denaturation, aggregation, loss of glycemic efficacy, and high risk of inducing anti-drug antibodies in diabetic patients.
2. **Illicit Distribution Networks:**
   - Stolen or compromised stocks are typically reintroduced into unauthorized grey-market retail channels, discount e-pharmacies without valid purchase invoices, or unlicensed medical stores.
   - Any distributor or retailer offering prescription biologicals without a traceable cold-chain data-logger certificate or licensed wholesaler invoice is operating in violation of the Drugs and Cosmetics Rules, 1945.

#### 3. Mandatory Instructions to Chemists & Healthcare Institutions
- Retailers must verify batch numbers of all received temperature-sensitive supplies against CDSCO transit alerts before dispensing.
- Maintain electronic cold-chain loggers and reject consignments arriving with broken security tamper-evident seals.
- Suspicious sales approaches by unauthorized agents must be reported immediately to the State Drugs Controller and CDSCO Zonal offices.
"""
    },
    {
        "filename": "CDSCO_Clinical_Monograph_NSQ_Laboratory_Failures.md",
        "title": "CDSCO Technical Monograph: Clinical Significance of Pharmaceutical Quality Deficiencies",
        "content": """# Central Drugs Standard Control Organisation (CDSCO)
## Central Drugs Laboratory (CDL), Kolkata & Regional Testing Laboratories (RDTL)
### Technical Reference: Clinical & Pharmacokinetic Consequences of Not of Standard Quality (NSQ) Findings

#### 1. Purpose of Laboratory Quality Assessment
The Central Drugs Testing Laboratories evaluate market samples drawn by regulatory inspectors under Section 25 of the Drugs and Cosmetics Act. Samples that fail to meet Indian Pharmacopoeia (IP) standards are categorized as Not of Standard Quality (NSQ). This monograph outlines the therapeutic implications of standard test failures.

#### 2. Common NSQ Failure Categories and Therapeutic Risks
1. **Dissolution Test Failure (In Vitro Drug Release):**
   - *Pharmacokinetic Impact:* Dissolution measures the rate at which the active pharmaceutical ingredient (API) dissolves from the solid dosage form into the gastrointestinal fluid. Formulations failing dissolution (e.g. Paracetamol, Metformin PR, or Pantoprazole) fail to achieve therapeutic plasma concentrations (Cmax).
   - *Clinical Consequence:* In chronic conditions (e.g. diabetes or hypertension), dissolution failure results in therapeutic failure, sustained hyperglycemia, or rebound hypertensive crises. In analgesics, it leads to lack of pain relief, causing patients to dangerously double-dose.
2. **Assay Test Failure (Sub-Potency or Super-Potency):**
   - *Sub-Potency (<90% of stated active claim):* Frequent in antibiotic tablets (e.g. Clavulanic acid assay failing at 70% to 80%). Low antibiotic concentrations fail to eradicate bacterial infections and directly drive antimicrobial resistance (AMR).
   - *Super-Potency (>110%):* Uncontrolled granulation or blending errors resulting in toxic plasma peaks, particularly hazardous for narrow therapeutic index drugs.
3. **Sterility Test Failure (Injectable & Ophthalmic Solutions):**
   - *Clinical Risk:* Intravenous fluids (e.g. Normal Saline, Dextrose, Ringer Lactate) failing sterility contain viable microbial flora or endotoxins. Infusion of non-sterile solutions triggers septic shock, pyrogenic reactions, systemic bacteremia, and fatality.
4. **Presence of Toxic Impurities & Contaminants:**
   - *Nitrosamines (NDMA / NDEA):* Known genotoxic carcinogens originating from solvent recovery or synthesis pathways (observed in contaminated Ranitidine and Sartans).
   - *Diethylene Glycol (DEG) / Ethylene Glycol (EG):* Highly toxic contaminants in solvent excipients (Propylene Glycol, Glycerin) used in pediatric cough syrups. DEG causes acute kidney injury, metabolic acidosis, encephalopathy, and pediatric mortality.
"""
    },
    {
        "filename": "CDSCO_SOP_Consumer_Action_Recalls_PvPI_Reporting.md",
        "title": "CDSCO Standard Operating Procedure: Consumer Action on NSQ/Spurious Medicines & PvPI Reporting",
        "content": """# Central Drugs Standard Control Organisation (CDSCO)
## Pharmacovigilance Programme of India (PvPI) & Indian Pharmacopoeia Commission (IPC)
### Standard Operating Procedure: Patient Action, Quarantine Protocol & Adverse Reaction Reporting

#### 1. Immediate Patient Safety Protocol upon Suspecting a Substandard Medicine
If a consumer, caregiver, or healthcare professional discovers that a medicine batch they possess is flagged as NSQ or Spurious by CDSCO:
1. **Immediate Cessation:** Stop taking the affected batch immediately. Do not discard or throw the medicine into domestic trash or water bodies.
2. **Medical Consultation:** Contact the prescribing physician or qualified medical officer immediately to obtain a safe, verified alternative batch or formulation, particularly for critical medications (cardiac, diabetic, or anti-epileptic therapies).
3. **Physical Quarantine:** Preserve the remaining tablets, strip, syrup bottle, or ampoule along with the purchase bill, cash memo, and outer carton. The physical sample is essential legal evidence for state drug control investigations.
4. **Pharmacy Return:** Return the quarantined batch to the dispensing pharmacy or hospital pharmacy. Under Rule 65 of the Drugs and Cosmetics Rules, retailers are legally obligated to accept recalled stock and provide credit or refund.

#### 2. Submitting an Adverse Drug Reaction (ADR) to PvPI
Patients experiencing unexpected side effects, lack of efficacy, or toxic symptoms must file an ADR report:
- **Toll-Free Helpline:** PvPI National Coordination Centre: 1800-180-3024 (9:00 AM to 5:30 PM IST weekdays).
- **Mobile Application:** ADR PvPI (Available on Google Play & iOS).
- **Email Submission:** pvpi.compat@gov.in or direct report via the MedVerify Community Reporting module.

#### 3. Penal Provisions Under the Drugs & Cosmetics Act, 1940
- Section 27(a): Manufacture, sale, or distribution of spurious or adulterated drugs that cause death or grievous hurt is punishable with imprisonment for a term which shall not be less than 10 years, extendable to life imprisonment, and a minimum fine of Rs 10,00,000 or three times the value of the confiscated goods.
- Section 27(b): Non-conforming or Not of Standard Quality drugs carry imprisonment of 3 to 5 years with mandatory statutory fines.
"""
    }
]
