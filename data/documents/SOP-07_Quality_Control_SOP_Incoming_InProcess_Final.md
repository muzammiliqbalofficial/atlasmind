# Atlas Honda Limited - Standard Operating Procedure
**Document ID:** SOP-07  
**Classification:** Internal - Quality Assurance, Production Engineering & Plant Assembly  
**Effective Date:** January 1, 2024  
**Version:** Version 1.0 – Sample  
**Approved by:** General Manager Quality Assurance & Senior Japanese Technical Advisor  
**Applicability:** Karachi Mother Plant & Sheikhupura Manufacturing Plants  
**Motorcycle Models Covered:** CD70, CD70 Dream, CG125, CG125 Self, CB125F, CB150F, Pridor  

> *Note: Sample Document for AtlasMind Prototype – Not Official*

---

## 1. Quality Policy & Foundational Mandate
Atlas Honda’s corporate quality policy is **"Right Work in First Attempt and On Time"**. Every motorcycle rolling off our assembly line carries our reputation for reliability, safety, and durability. 

Quality is built *into* the manufacturing process—not merely inspected at the end. All personnel follow the three golden principles: **Do Not Accept Defects, Do Not Produce Defects, and Do Not Pass Defects downstream**.

---

## 2. Incoming Quality Control (IQC) - Supplier & Raw Material

### 2.1 Receiving Inspection Sampling Plan
- All vendor components (castings, forging parts, carburetors, electrical wiring harnesses, tires, fuel tanks) received at the Logistics Receiving Bay must undergo IQC before physical transfer to raw material stores.
- Inspections follow **ISO 2859-1 (Sampling Procedures for Inspection by Attributes)** using Normal Single Sampling Level II:
  - **Critical Defect (AQL 0.00):** Functional defects affecting rider safety (e.g., front fork casting flaws, brake lining crack, fuel cock leakage). Zero acceptance number ($Ac = 0$).
  - **Major Defect (AQL 0.65):** Dimensions out of tolerance, threading pitch error, harness connector mismatch.
  - **Minor Defect (AQL 4.00):** Packaging damage, cosmetic plating scratch not visible under normal light.

### 2.2 Material Rejection & VCAR Procedure
- Batches failing AQL thresholds are flagged with Red Quarantine Hold Tags and moved to the Secure Defective Material Cage.
- An automated **Vendor Corrective Action Request (VCAR)** is triggered in SAP QM within 24 hours. The vendor must provide an 8D Root Cause Analysis report within five (5) working days before subsequent shipments are reviewed.

---

## 3. In-Process Quality Control (IPQC) - Plant Fabrication & Assembly

### 3.1 Press & Stamping Shop Checkpoints
- First-off and Last-off Part Inspection at every die setup change (evaluating draw depth, burr height $< 0.05$ mm, flange flatness).
- Coordinate Measuring Machine (CMM) verification of frame stamping jig geometries on daily random samples.

### 3.2 Robotic & Manual Welding Line Checkpoints
- **Weld Penetration Macro-Etch Test:** One welded chassis frame per shift is destructively sectioned, polished, etched with 5% Nital solution, and examined under an optical metallurgical microscope. Minimum required weld penetration is **$80\%$ of base metal thickness**.
- Visual inspection of all bead profiles: No blowholes, spatter, lack of fusion, or undercuts allowed.

### 3.3 Critical Torque Tightening Standards
- All safety-critical threaded fasteners must be tightened using calibrated digital torque wrenches with automated data logging (Poka-Yoke error proofing):
  - Front Axle Nut: $55 - 65 \text{ N}\cdot\text{m}$
  - Rear Axle Nut: $80 - 90 \text{ N}\cdot\text{m}$
  - Engine Mounting Bolts: $35 - 45 \text{ N}\cdot\text{m}$
  - Handlebar Clamp Bolts: $22 - 28 \text{ N}\cdot\text{m}$
- Torque tools must be calibrated every 15 days by the Metrology Calibration Laboratory.

---

## 4. Final Assembly & Pre-Delivery Inspection (PDI)

Every completed motorcycle rolling off the final conveyor must pass through 100% End-of-Line testing:

### 4.1 Roller Dynamometer Test Booth
- **Speedometer Calibration:** Calibrated against dynamometer rollers at 40 km/h and 60 km/h ($\pm 5\%$ tolerance).
- **Brake Force Efficiency:** Front and rear brake efficiency tested on load cells; minimum combined braking efficiency must exceed **$60\%$ of gross vehicle weight**.
- **Engine Tuning & Emissions:** Measurement of exhaust gas using NDIR 4-gas analyzer:
  - Carbon Monoxide (CO): $\le 2.5\%$ at idle (exceeding Sindh Environmental Quality Standards limits).
  - Hydrocarbons (HC): $\le 450 \text{ ppm}$ at idle.

### 4.2 Dynamic Test Track Evaluation
- Every motorcycle undergoes a 1.2-kilometer functional test run on the Karachi Plant outdoor proving track:
  - Gear shifting smoothness across all four gears.
  - Clutch engagement without slippage or chatter.
  - Suspension rebound damping over rumble strips and rough pavement.
  - Absence of abnormal engine knocks, rattling, or bearing noises.

### 4.3 Final Quality Gate Release
- Once cleared, the Lead Quality Inspector affixes the green **"Atlas Honda QA Approved"** serialized tamper-evident hologram on the front fork stem.
- Unapproved units are immediately routed via shunt rails to the Rectification Bay.
