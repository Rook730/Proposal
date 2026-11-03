%% Convenient Enterprises requirement library (URS/RFQ Template Rev 1.0, Nick Matney).
%% Parsed by ce_urs.parse_library on first use; the data folder then keeps profiles/ce/requirements.json.
%%
%% Headings: "#" level 1, "##" level 2, "###" level 3. Attributes in braces at the end of a heading line:
%%   kind=information|requirement|instruction|data   applies=tag[,tag]   unnumbered   off   pagebreak
%% Body: paragraphs, "- " bullets (two spaces per nesting level), pipe tables, **bold**, *italic*.
%%   [!text] is a template note (blue, dropped from an issued URS); other [text] is a blank to fill in (blue,
%%   flagged until filled). {name} is a variable.
%%   A line "- {name}" with a list variable expands into one bullet per line of its value.
%%   {?tag} ... {/?} keeps the lines only when the tag is yes; {?!tag} ... {/?} only when it is no.
%%   "::form" ... "::" lines are signature/contact rows ("Label" or "Label | Label").
%% Blocks "::: tag", "::: var", "::: topic" define intake questions.

::: topic company
title: Your company
:::

::: topic product
title: Your product
:::

::: topic today
title: Your process today
:::

::: topic machine
title: What the machine must do
:::

::: topic volumes
title: Volumes and shifts
:::

::: topic utilities
title: Plant utilities
:::

::: topic safety
title: Safety
:::

::: topic documentation
title: Documentation
:::

::: topic timeline
title: Timeline and budget
:::

::: tag pneumatics
topic: machine
question: Will the machine use compressed air (cylinders, valves, air tools)?
:::

::: tag hydraulics
topic: machine
question: Will the machine use hydraulics (hydraulic cylinders, a power unit)?
:::

::: tag plc
topic: machine
question: Will the machine have a PLC and an operator touchscreen (HMI)?
:::

::: tag recipes
topic: machine
question: Will the machine run different products that need saved settings (recipes)?
:::

::: tag interfaces
topic: machine
question: Does the machine need to connect to or communicate with other equipment (a tester, a dispenser, another machine)?
:::

::: tag tooling
topic: machine
question: Will the supplier provide tooling, fixtures or gauges for your parts?
:::

::: tag fatsat
topic: documentation
question: Include the FAT/SAT plan (how the machine is tested and accepted at the supplier and at your plant)?
:::

::: var plant
type: text
topic: company
question: What is the plant called in the document (usually its town)?
example: Murphy
default: [ADDRESS]
:::

::: var system_task
type: text
topic: machine
question: In a few words, what will the machine do?
example: press bushings into brake brackets and leak test them
default: perform a task
:::

::: var system_context
type: text
topic: today
question: Will it replace existing equipment? Describe it in a few words, or say it is new.
example: replace a manual press station
default: replace an outdated System of the same function
:::

::: var need_reasons
type: list
topic: machine
question: Why is the machine needed? One reason per line.
example: To remove the operator from the pinch point
default:
  To eliminate quality issues arising from the inconsistencies associated with performing the operation with the current System.
  To provide the necessary hardware for future integration with other equipment. The machine will be installed and operated at {plant}.
:::

::: var current_steps
type: list
topic: today
question: How is the job done today? One step per line, from material arriving to leaving the cell.
example: Operator loads two brackets into the fixture
default:
  [Material arrives at the cell in a condition]
  [Material is fed into the operation]
  [Operator interacts with the machine and material]
  [Material is processed]
  [Material is outfeed]
  [Material leaves the cell in a condition]
:::

::: var min_length
type: text
topic: product
question: Smallest part: length (with units)
example: 4.5 in
default: [ ]
:::

::: var min_width
type: text
topic: product
question: Smallest part: width
default: [ ]
:::

::: var min_thickness
type: text
topic: product
question: Smallest part: thickness
default: [ ]
:::

::: var min_weight
type: text
topic: product
question: Smallest part: weight
default: [ ]
:::

::: var max_length
type: text
topic: product
question: Largest part: length (with units)
example: 12 in
default: [ ]
:::

::: var max_width
type: text
topic: product
question: Largest part: width
default: [ ]
:::

::: var max_thickness
type: text
topic: product
question: Largest part: thickness
default: [ ]
:::

::: var max_weight
type: text
topic: product
question: Largest part: weight
default: [ ]
:::

::: var cycle_now
type: text
topic: volumes
question: How long does one part take today (cycle time)?
example: 49 seconds
default: [ ]
:::

::: var takt_now
type: text
topic: volumes
question: How often does a part need to be finished to keep up with demand today (takt time)? Leave blank if unknown.
example: 60 seconds
default: [ ]
:::

::: var volume_now
type: text
topic: volumes
question: How many parts a year today?
example: 120,000
default: [ ]
:::

::: var cycle_future
type: text
topic: volumes
question: Target cycle time for the new machine
default:
:::

::: var takt_future
type: text
topic: volumes
question: Target takt time for the new machine
default:
:::

::: var volume_future
type: text
topic: volumes
question: Expected parts a year with the new machine
default:
:::

::: var operating_schedule
type: text
topic: volumes
question: How many hours a day and days a week will it run?
example: 16 hour/day x 5 days/week
default: 24 hour/day x 6 days/week
:::

::: var control_interfaces
type: list
topic: machine
question: How will operators control it? One per line (touchscreen, pushbuttons, lights, foot pedal...).
default:
  Digital HMI
  Pushbutton/Switch
  Indicator
  Footpedal
:::

::: var process_inputs
type: list
topic: machine
question: What goes into the machine (materials, parts, conditions)? One per line.
default:
  Raw material A
  Raw material B
  Condition A
  Condition B
:::

::: var process_outputs
type: list
topic: machine
question: What comes out (finished goods, data)? One per line.
default:
  Finished good A
  Finished good B
  Data A
  Data B
:::

::: var loading_methods
type: list
topic: machine
question: How should parts be loaded into the machine? One per line.
default:
  Method A
  Method B
:::

::: var consumption_methods
type: list
topic: machine
question: How should the machine use up or process the parts? One per line.
default:
  Method A
  Method B
  Operator Intervention
  Quality Requirements
:::

::: var process_steps
type: list
topic: machine
question: What should the machine do, in order? One step per line; indent details with two spaces.
example: Clamp both brackets
default:
  Step 1
    Process Detail A
    Process Detail B
  Step 2
    Process Detail A
    Process Detail B
  Step 3
    Process Detail A
    Process Detail B
  Step 4
    Process Detail A
    Process Detail B
  Step 5
    Process Detail A
    Process Detail B
:::

::: var plant_environment
type: text
topic: utilities
question: Describe the plant climate (heated, air conditioned, temperature range, humidity).
example: heated, but not air conditioned, and the ambient temperature can range from 55-105 deg F
default: heated, but not air conditioned, and the ambient temperature can range from 55-105 deg F
:::

::: var interface_devices
type: list
topic: machine
question: Which other equipment must it connect to? One per line.
default:
  Tester
  Dispenser
  Machine
:::

::: var power_available
type: text
topic: utilities
question: What electrical power is available at the machine location?
example: 60 Hz frequency 110V 1-phase and 480V 3-phase
default: 60 Hz frequency 110V 1-phase and 480V 3-phase
:::

::: var air_pressure
type: text
topic: utilities
question: Plant compressed air pressure
example: 80 psi
default: 80 psi
:::

::: var other_utilities
type: text
topic: utilities
question: Any other utilities available (nitrogen, water, vacuum)?
example: available dry nitrogen supplied at 250 psi
default: available dry nitrogen supplied at 250 psi
:::

::: var noise_limit
type: text
topic: safety
question: Maximum noise level at the operator
example: 80 dBA
default: 80 dBA
:::

::: var support_days
type: text
topic: timeline
question: Days of on-site training and support after installation
default: 5 days
:::

::: var support_window
type: text
topic: timeline
question: Within how long after installation must those days be used?
default: 6 months
:::

::: var target_date
type: text
topic: timeline
question: When does the machine need to be running? (Intake only, not printed.)
example: Second quarter 2027
default:
:::

::: var budget
type: text
topic: timeline
question: Is there a budget or budget range? (Intake only, not printed.)
default:
:::

# Introduction {kind=information}

## Summary {kind=information}

{company}, is seeking proposals for a System to {system_task}. This System will {system_context}.

The cell is needed:

- {need_reasons}

For brevity within this document: *Consumer* indicates {company} {plant}; *Provider* indicates the Provider of the equipment; and *System* indicates the overall production line machine(s) and components provided by the *Provider*.

## Project Adherence {kind=requirement}

This document will serve to capture the Consumer's requirements and/or expectations for the System. The final revision of this document, along with the Provider's quotation, and the Consumer's purchase order, will form the legal contract for the purchase agreement. Any proposed deviations or corrections must be identified on the "URS Response Form - Deviations or Corrections" provided. If the Provider does not indicate a deviation or correction, then it is assumed that the proposed System will comply with the requirements of this document's newest revision level and of the purchase agreement.

## Confidentiality Agreement {kind=requirement}

The concepts, ideas, and any other documentation contained in this URS/RFQ and URS/RFQ package shall be considered the property of the Consumer and shall be protected under a Confidential Disclosure Agreement (CDA). If the Provider does not have a current signed copy of a CDA with the Consumer inform the Consumer immediately and delete all copies of documents which have been provided

## Project Conceptualization and Quoting {kind=requirement}

The quotation and/or supply of the System by the Provider is to be based on either: the Consumer's concept(s) and any options requested for the System; or Provider recommended alternate methods for completing the requirements of this specification. If the Provider wishes to quote a System that is different in its supply and/or concept from the Consumer concepts/options, the Provider may quote these recommended Systems for consideration by the Consumer.

If the Provider quotes the System utilizing the Consumer's concept(s) and a System is purchased from Provider that is in adherence to the Consumer's concepts/options, the Provider agrees that this supply, per the Consumer purchase order and Provider quotation, is the complying design and supply for the System with all responsibilities encompassed by the Provider for adherence to the Provider's quotation, the latest revision of this specification, and the Consumer's purchase order.

The Consumer's intent is to purchase a turn-key System which requires no integration at the Consumer's site. All integration should be complete at the Provider.

## Quoting {kind=instruction}

The Consumer requires the following features to be present in a final quotation. This list should not be considered limiting, quotes should be as detailed as necessary to convey the Provider's plan. Items which do not apply to the System should be listed as N/A. Budgetary quotations are not required to contain all the following but should be complete enough to convey System functionality and provide approximate cost and delivery information.

- All quotations shall include delivery and cancellation terms and provisions.
- The Provider must provide any software which is required to program, monitor, or control the equipment. This may be waived if the Consumer has a current licensed copy of any required software. The Provider must provide any hardware, other than a standard PC, which is required to program, monitor, or control the equipment.
- Full System Description including but not limited to:
  - Loading/Unloading
  - Machine layout
  - Cell layout
  - Data collection/management scheme
  - Controls functionality and operational modes
  - HMI screens (Title and/or example only. Full content not required)
  - Order of Operations (For both automated and manual operational modes)
  - Quality checks (if applicable)
  - Estimated cycle time (Breakdown manual/automatic operations)
  - Make and Model of all purchased off-the-shelf equipment (>$1k)
  - Recipe layout and ingredients (as applicable)
- Timeline
  - Weekly or bi-weekly progress updates are expected depending on project scope. [!To be determined at time of quotation]
  - Design approval
  - Design acceptance
  - Factory Acceptance Testing (FAT) plan
  - Delivery
  - Site Acceptance Testing (SAT) plan
- Miscellaneous Line Items
  - Tooling/gauging costs are to be separated from capital equipment costs
  - All major purchased components (>$10k)
  - On-site training and support for the duration of System installation
  - Additional on-site training and support for {support_days} (to be used consecutively) to be used within {support_window} of System installation at Consumer's site. All time not used will be forfeit if not used in the time allotted and additional contracture will be necessary for further on-site support.
  - Extended warranty [!Duration to be determined by the Consumer and conveyed to Provider at time of quotation]
  - Any and all options/alternatives determined by the Consumer or Provider [!Specifics determined at time of quotation]

## URS/RFQ Package Contents {kind=information}

This URS/RFQ package contains documents that will be necessary to quote the requested System. It also contains documents which will used by {company} to qualify the System after construction. Below is a list of the documents and templates which can be found alongside this URS/RFQ.

- All applicable product drawings in pdf format. 2D or 3D models may be available upon request.
- TAKT time analysis
- System layout constraints
- 3P Process Evaluation Checklist
- Physical Demands Analysis Template
- Factory Acceptance Test Plan (Template provided. Plan will be completed and provided prior to final quotation)
- Site Acceptance Test Plan (Template provided. Plan will be completed and provided prior to final quotation)

# Current Process and Product Data {kind=data}

## Current Process Steps {kind=data}

- {current_steps}

Picture(s) or video(s) of the current process/equipment will be provided alongside this URS/RFQ

## Product Scope {kind=data}

Short description of parts, products, or components which are used/consumed by this System. Note that the minimum and maximum conditions noted below may not all appear on the same part.

- Minimum:
  - Length: {min_length}
  - Width: {min_width}
  - Thickness: {min_thickness}
  - Weight: {min_weight}
- Maximum:
  - Length: {max_length}
  - Width: {max_width}
  - Thickness: {max_thickness}
  - Weight: {max_weight}

## Product Prints {kind=information}

Provided alongside this URS/RFQ is a folder containing all relevant part prints. This information is being supplied to depict the characteristics of each finished part, the configuration of the components, as well as the interface of any new equipment to be quoted

## Process Data {kind=data}

- Cycle Time
  - Current State: {cycle_now}
- TAKT Time
  - Current State: {takt_now}
- Annual Volume
  - Current State: {volume_now}

# System Requirements

## Control Interfaces

Any operator interface for primary and/or secondary Systems, is to be designed and supplied with a minimum of one following components. Additional interface options not listed here should be verified with Consumer engineers. (Consumer specific requirements for these components can be found in Section 5):

[!Update the below list as needed to suit your specific requirements]

- {control_interfaces}

## Process Parameters

[!Modify the below paragraphs as necessary to suit your specific requirements]

The new System will be designed and supplied with the consideration that the Consumer will continue to utilize the current System during build, test, and install of the new System.

New equipment supply, mounting location/method, and/or accessibility must not be a hindrance in the ability for an operator to produce product on the existing equipment.

- Process Inputs
  - {process_inputs}
- Process Outputs
  - {process_outputs}

## Loading and Alignment

[!Modify the below paragraphs as necessary to suit your specific requirements]

The System provided by the Provider must include a method and required equipment to introduce and properly align all raw material inputs for accurate and repeatable processing. An operator shall be able to manually process raw material through the System in the case that manual operation is required, or auto operation is unavailable.

### Component Loading

The method to introduce components into the System will be designed and supplied with the following considerations:

In the process of loading material, the operator shall not encounter mechanical, electrical, pneumatic, or other hazards.

- {loading_methods}

### Component Consumption

The method to consume the components in the System will be designed and supplied with the following considerations:

- {consumption_methods}

## Process Flow

The System is expected to perform the following functions in the order described below using any specific hardware called out therein. Any deviation from this operation order must be approved by {company} Engineers. All operations are expected to be performed by a single operator unless otherwise specified.

- {process_steps}

## Process Data {kind=data}

[!Additional data may be added here as necessary to suit your specific requirements. Information regarding current division of labor within the cell may be beneficial.]

- Cycle Time
  - Future State: {cycle_future}
- TAKT Time
  - Future State: {takt_future}
- Annual Volume
  - Future State: {volume_future}

## Cosmetic or Functional Defects

No damage, breakage, marking or scuffing of the finished product, through contact with the normal operations of the System are allowed. Refer to part prints for surface finish requirements. Any applicable engineering specifications will be provided as needed.

## Changeover Time

Changeover should be eliminated where possible. If not possible to eliminate entirely, effort should be taken to minimize operator interaction and reduce time through Single Minute Exchange of Dies (SMED) methodologies.

## System Size

[!Modify the below paragraphs as necessary to suit your specific requirements]

The completed and installed System must fit within the current production line work cell area with minimal changes. A dimensional drawing of current equipment and proposed footprint will be provided as part of the URS/RFQ package.

## System Durability

The System shall be designed and constructed for minimal downtime and years of reliable service in a {operating_schedule} production environment.

The equipment shall be constructed to prevent rusting or corrosion in the plant environment specified below, processing the materials specified and utilizing any lubricants and fluids required.

## Plant Environment

[!Modify the below paragraphs as necessary to suit your specific requirements. Specify controlled environment if applicable.]

The {plant} plant at large is {plant_environment}. The plant relative humidity varies greatly based on the seasonal conditions and is not tracked or controlled.

Equipment supplied with System should be able to withstand the general plant environment. If there is a design constraint which necessitates the System be in a climate-controlled environment, the Consumer should be notified.

## Maintenance

The System and its included equipment shall be designed and constructed to facilitate easy cleaning including smooth, cleanable, impervious surfaces, joints are minimized, sealed, welds are cleaned, ground and polished. Corners have radius or are well sealed. No sharp edges are allowable in any operator or maintenance access areas.

## Component Availability

Where possible, the Provider shall select components that are current, supported, readily available, stocked components for ease of replacement and shall avoid selecting components that may be difficult to source, are obsolete, or are being phased out. Exceptions can be made with approval from {company} engineers.

## Interface Devices

[!Modify the below paragraphs as necessary to suit your specific requirements. Some systems will not interface with external systems and the 1st paragraph below should be removed along with the bullet points.]

{?interfaces}
The items below are integral to the operation of the System and consideration will need to be provided to interconnect, communicate, or otherwise interface with for the design of the new System.

- {interface_devices}
{/?}
{?!interfaces}
There are no external devices integral to the operation of the System and no consideration will need to be provided to interconnect, communicate, or otherwise interface with for the design of the new System.
{/?}

# Safety Features

The design and construction must be compliant with the Occupational Safety and Hazards Act (OSHA) standards, the National Electric Code (NEC), National Fire Protection Act (NFPA), state, local, and any other applicable standards or codes.

A {company} Environmental Health and Safety Department representative shall check machinery and equipment supplied at or before FAT for safety compliance. Any issues shall be resolved before System shipment and delivery.

## Guarding

- Guarding must be provided to protect the operator and other employees in the area from hazards such as those created by moving parts, moving product, nip points, rotating parts, drives, shafts, chains, gears, robots, etc., and must be compliant with OSHA requirements for each of these instances.
- All guards shall be affixed to the machine where possible and secured elsewhere if for any reason attachment to the machine is not possible, or if the guarding is an access point to the machine.
- The guard shall be electrically interlocked to disrupt all machine functions if it is not in place.
- The guard shall be such that it does not offer an accident hazard itself.
- The guard shall utilize fasteners requiring tools to remove, to minimize the possibility of misuse or removal.
- The Consumer's preference for point of operation devices are presence-sensing devices, (i.e. light curtains, scanners, etc.), any deviation in design must be approved by the {company} Environmental Health and Safety Department. A presence-sensing device (PSD) shall protect the operator by preventing or stopping the normal operations of the machine if any body part is placed into the point of operation. The Provider will provide the formula and calculations used to size and place the PSD.

## Noise

Equipment noise levels must be below {noise_limit} at three feet from the noise source (or at the Operator's normal working position, whichever is closer) in normal automatic mode with parts.

Note: If equipment exceeds the aforementioned sound limit or the "best achievable" sound limit quoted and acceptable by the Consumer, the Provider shall request written permission to ship the equipment. The Provider must submit in writing, upon request to ship, detailing of the feasible engineering controls currently designed into and/or installed on the equipment. Shipping the equipment does not release the Provider from the responsibility to meet the specified sound limitations.

## Ventilation

The Consumer is dedicated to maintaining a clean, uncontaminated atmospheric industrial work environment. Any hazardous or non-hazardous particulate, gases, vapors and/or mists necessitates the use of a ventilation system. All ventilation systems must be designed using an approved American Conference of Governmental Industrial Hygienist method.

## Compressed Media

All pressurized piping, hoses, tubing, and their connections must be secured and shielded sufficiently for the pressures anticipated to prevent failure, leaking, or spray of compressed media.

## Electrical Components and Connections

All electrical components must be properly shielded, insulated, and sealed to prevent personal injury or short circuit of electrical components due to spilled liquids or cleaning of the equipment with liquids. Electrical enclosures, wiring, and conduit shall be constructed and rated appropriately for the environment in which it will be installed. Any extraneous environmental conditions will be conveyed at the time of quotation.

## E-Stops

Emergency stop button(s) (E-stops) must be located at convenient locations where the Operator may be located during operation.

- All emergency stop buttons shall be maintained push/pull type, red in color and all remotely located operator stations shall be equipped with their own device.
- After power failures, provisions shall be made to prevent machines from automatically restarting upon restoration of power.

## Safety Device Circuits

E-stop and safety interlock circuits must be hard-wired to a master control relay and not directly through PLC logic (unless a Safety PLC is used). The PLC must monitor the status of the master control relay and de-energize non-safety electrical components when the e-stop or interlock circuits are tripped.

Safety circuits must include dual-redundant relays monitored through a safety PLC or control relay

## Stored Energy and Lock-out / Tag-out

Stored Energy (electrical, compressed air, gravity, etc.) shall be released when an e-stop is activated, or an interlocked guard is opened, if possible. Any devices that will retain stored energy in the event of an E-stop/interlock must be specified in the operations manual.

The energy controlling components (switches, valves, power disconnects, etc.) must permit the installation of isolation devices and padlocks included for application of lock-out tag-out devices during required maintenance or service.

## Operator Ergonomics

A Physical Demands Analysis shall be performed on all equipment prior to acceptance (provided in the URS/RFQ package) by the Consumer.

The goal of Provider's design is to promote ease and efficiency for the person working. Equipment to be designed and supplied with the following, but not limiting, considerations:

- Clearance for the operator's body for entrance and egress. (Including emergency exit)
- Suitable body posture at work. (Including space for changing positions)
- Operation of controls and equipment without bumping elbows, knees, head, etc.
- Operation of controls and equipment without blocking visual observation of equipment
- The avoidance of excessive forces
- No team-lift required. (>30lbs)
- All machine-mounted devices shall be readily accessible per good ergonomic practices. Conduits, piping or machine sections shall not limit accessibility

# Electrical and Control Specifications

## Common Electrical Standards

Consumer Engineering must approve any deviation from these specifications or any of the specified industrial standards.

- Design and installation of electrical components shall conform to the latest NEC and OSHA standards. Any other applicable standard shall also be followed.
- All electronic equipment shall conform to the latest electronic standards for Industrial Equipment. Electrical equipment is to be housed in NEMA 12 or better enclosures. Enclosures shall be sized to not require cooling.
- All wiring shall be machine tool grade, heat and oil resistant. The wire color shall be as follows:
  - Green = Earth Ground
  - Black VAC > 120 V
  - Red = 120 VAC
  - White = 120 VAC common
  - Blue = DC & DC components
  - White / Blue Stripe = 24 VDC common
  - Yellow = Remote Power

## Control Panel and Devices

- All I/O racks shall be clearly marked, and wires labeled with corresponding PLC address. All discrete input and outputs shall be wired to a terminal strip.
- All circuits and devices greater than 120 Volts shall be "Safe Touch". Safe Touch is defined as the ability to work on or near device without being exposed to electrical hazard. Examples of Safe Touch include but are not limited to: plastic covers with probe access over 480V fuses and distribution blocks, and terminals with recessed contacts and screws.
- All fuses and circuit breakers shall be labeled and mounted on back plate where possible. Circuit breakers are preferred, but where necessary, fuses may be used. Where not mounted on back plate, fuses and circuit breakers must be guarded. Each fuse or circuit breaker shall have its own discrete input to the PLC for diagnostics.
- E-Stop buttons and all devices in the master control relay circuit shall have their own input for diagnostic purposes.
- Cable trays are to be the slotted type, with no covers longer than 36 inches.
- All control circuits shall be 24 VDC unless otherwise approved.
- All pilot and indicator lights shall be oil tight.
- Push buttons and selector switches shall be oil tight and arranged on operator panel in order (left to right) to follow the manual operating sequence.
- All solenoids, devices and relays will have 24VDC coils with free-wheeling diodes (rated at 600 volts or higher). Each device will be wired to its own PLC output or breakout device; solenoids shall be fused with individual indicating devices.
- All relays and other devices in the control panel shall be arranged in consecutive numerical order. A permanent nameplate held by some mechanical means, on or near the device shall identify each device. This nameplate shall be visible when panel is completely wired.
- Control panel shall have terminal blocks numbered in numerical order and containing test points for all machine mounted devices. Terminal block mounting channel shall have 1.5" metal spacers behind them for ease of wiring and sufficient space on both sides to permit easy installation and checking of wires. High density terminal blocks are not preferred but may be used with approval.
- All wires in the panel shall be numbered on both ends to conform to schematic diagram. 10% spare wires shall be provided. Wire numbers and letters shall be of 7/8" vinyl labels or equivalent.
- Panel shall include an external PLC programming connector, HMI programming connector, and 115 VAC programming power duplex plugs for access without opening the cabinet. Location shall be pre-approved by the Consumer.
- The System shall have a single electrical feed and safety disconnect switch unless otherwise noted.
- Provider to provide 20% additional controls capacity including memory, input/output PLC terminal space, and space in the electrical enclosure, for potential future expansions of capabilities.

## Machine Mounted Devices

- All machine-mounted devices shall be numbered to correspond to schematic diagram by means of a permanent engraved plate on or adjacent to the device and held by mechanical means. Adhesive tags are not permissible.
- When possible, non-contact sensors, proximity switches and other machine-mounted devices shall be a quick disconnect design, oil tight, and labeled by means of an engraved plate which is traceable to the appropriate wiring diagram for title and I/O number.
- A switch or other non-contact device shall be used to indicate full travel at both ends on all mechanical functions. Timers or pressure switches are not an acceptable means of indicating or assuming full movement.
- Photoelectric devices shall include an indicator light to indicate correct alignment and actuation.
- Switches or sensors shall have a visible indicator on the switch or its mating controller, or as part of the connector.

## Programmable Logic Controller (PLC) and Human Machine Interfaces (HMI) {applies=plc}

### Program Retention

- The Provider shall save copies of the final shipped versions of all software (PLC ladder logic, HMI code, etc.) within their retention Systems for the expected life of the System or a minimum of 10 years.
- The Provider will communicate on-going upgrades and patches needed to sustain the machine.
- The Provider shall also supply a back-up copy, saved on memory device, of all software with the final machine documentation package, including product recipes.

### Hardware

- The Provider shall provide Rockwell Automation Allen-Bradley MicroLogix PLC (CompactLogix, ControlLogix, or GuardLogix PLCs can be used with written approval from the Consumer) if a PLC is required for the System. [!Specifics determined at time of quotation]
- The machine will have a color touchscreen interface of 5" or greater. Interface options are Industrial Panel PC or an Allen-Bradley PanelView. If a Panel PC is used, Ignition! Software shall be used as the HMI solution. [!Specifics determined at time of quotation]
- HMI must be protected in a suitable enclosure or articulating arm, convenient to the Operator work zone if required for the System.

### Control Access Levels

The HMI control System will limit screen and function access by different user levels (below) with password access. The Provider shall explain and recommend any additional access levels, functions allowed, and method of access control planned in the quotation. [!Specifics determined at time of quotation]

- Operator: Operate the machine using saved recipes - select a recipe, enter product and/or lot information, start/stop, acknowledge/clear alarms, etc.
- Maintenance: Above plus the ability to access control and alarm parameters; access station jog or manual operation functions; view controls and sensors input/output status, etc.
- Administrator/Engineer: All functions above plus the ability to create, modify, and delete recipes and all additional non-specified functions.

### Product Recipe {applies=recipes}

- The PLC or HMI will have a recipe management System whereby product recipes can be created, saved, exported to memory storage device, opened, closed, and modified. An individual recipe will include user-programmable settings (ingredients) for all adjustments possible.
- Recipes can be in one of several formats; examples include: xlsx, csv, txt, sql database, etc. Recipe format will be decided at the time of quotation.
- The machine shall include local storage/back-up of product recipes, and any other user programmed setup values, with use of USB flash drive, microSD, SSD, etc. for recovery of lost, corrupted, or revised files.
- Ingredient list for recipe will be developed through discussion during machine design phase.

### Alarms and Diagnostics

- The machine shall have a stack light to provide a visual alarm corresponding to alarms displayed on the HMI. The Provider shall recommend and explain the recommended alarms including HMI, audible and stack light.
- For Maintenance and Engineering troubleshooting purposes, a control status page, indicating the state of all components, PLC inputs and outputs, is preferred.

# Hydraulic Specifications {applies=hydraulics}

## Operating Pressures

- Hydraulic systems shall be designed to operate within a maximum pressure of 3,000 psi.
- Hydraulic equipment shall be designed to withstand the maximum pressure to which they may be subjected plus 50% over-rating.
- All pressure controls shall be marked to indicate minimum and maximum pressures by means of stamped metal or engraved plastic plates held by mechanical means on or adjacent to the control. Adhesive tags are not acceptable

## Pumps

- Pumps shall not be mounted inside the oil reservoir.
- Flexible couplings shall be used between pump and motor.
- Where pumps are operated in parallel, valves shall be installed to permit removal of one pump while other pumps remain in operation.
- A detachable safety guard shall be fastened over the coupling and shafts.
- Direction of rotation of each pump shall be clearly indicated on the pump by a metal identification plate. Printed or decal arrows are not preferred

## Solenoids

- Quick Disconnect type with indicator lights.
- Standard Wet Core.
- All pilot and directional valves shall be spring center or spring return types. Detent style valves require approval.

## Fluids

- All fluids power components, seals, external paint, labels, etc. shall be compatible with the fluid to be used.
- Each hydraulic reservoir shall have metal tag affixed near reservoir fill spout to identify the appropriate hydraulic fluid.
- List of inventoried hydraulic fluids. All fluids used must be approved by the Consumer in advance.

## Reservoirs

- Filler holes shall have a strainer for straining the fluid when filling.
- Reservoir shall be provided with markings to continuously show high and low levels of fluids with the pump running and high level with the pump stopped.
- Ample and readily accessible means shall be provided for cleaning the reservoir completely.
- Temperature gauges required on all tanks.

## Filters, Strainers, Flow Meters, and Gauges

- Replaceable, cartridge type, non-absorptive, 30-micron absolute, full flow, bypass when cartridge is plugged, filters shall be installed on the pressure side of the pump for all systems operating at 500 psig or less. Systems operating at pressures over 500 psig may incorporate the filter in the return line.
- Hydraulic systems utilizing solenoid-actuated hydraulic valves shall incorporate an additional 10-micron minimum absolute telltale hydraulic filter to further protect the valves.
- Filters shall have an external indicator to show degree of contamination. A simple gauge recording pressure drop across the filter is not acceptable.
- Filters and strainers shall be so installed so that it will not be necessary to drain the reservoir or disturb the piping for servicing.
- Filter identification tag shall include cartridge number.
- Pump suction risers shall include strainer of appropriate size, at least 74 micron strainer.
- All pressure gages shall be liquid filled with isolators.

## Piping and Tubing

Copper tubing shall not be used for conveying hydraulic fluids. Tubing shall conform to the following specifications:

- Hydraulic piping and tubing shall not be bundled. It shall be laid in parallel runs and securely fastened to the machine.
- Piping and tubing shall not be routed where it can serve as a step for personnel operating or repairing the machine. Cast iron clamps and one-hole pipe straps are not acceptable.

Heating and cooling water lines shall be copper, galvanized, PVC or stainless steel. Steel tubing or black pipe shall only be used with prior approval.

## Component Marking

All hydraulic devices shall be identified by means of a stamped metal plate mounted on or adjacent to the device and held by some mechanical means. Identification shall match component identification shown on hydraulic diagram. Adhesive tags are not acceptable

# Pneumatic Specifications {applies=pneumatics}

## Operating Pressures

- Pneumatic Systems shall be designed to operate effectively at a pressure of 70-80 pounds per square inch gauge.
- Pressure control required at each valve, or valve manifold, that requires the same operating pressure for valves contained within
- Pressure gauge required at each valve, or valve manifold.
- System shall be designed to pause operation and notify operator if pressure falls below the acceptable threshold.

## Safety Shut-off Valves

- Only one source of air supply shall be used for each piece of equipment.
- All pneumatic supply lines shall contain a 3-way shut-off valve with provisions for locking it in the off position. This valve shall comply with OSHA standard 29 CFR 1910.147 for general safety.
- All System piping shall be arranged to drain pressure from all prime movers when the main shut-off is in the closed or off position.

## Filters, Regulators, and Lubricators

- Airline filters shall be with replaceable shatter-proof transparent bowl and automatic drain.
- Airline regulators shall be relieving type with gauge. Use filter-regulator combination assembly where ever possible to reduce piping.
- Airline lubricators shall be with replaceable shatter-proof bowl. Lubricator use shall be approved by Consumer engineers.

## Directional Control Valves

- Pneumatic direction control valves should be manifold or panel mounted where piping can be simplified.
- All valves shall have indicator lights.
- Plug in style mandatory.
- Valves shall be spring center or spring return types. Detent style valves require approval.

## Mufflers

All air exhausts shall be equipped with mufflers.

## Cylinders

Cylinders shall have interchangeable mounting dimensions and shall have adjustable cushions and/or stops on both ends.

## Component Marking

All pneumatic components shall be labeled for identification by means of a stamped metal plate or engraved plastic tags mounted adjacent to, but not on the device and held by some mechanical means. Identification shall match component identification shown on pneumatic diagram. Adhesive tags are not acceptable

# Tooling, Fixturing, and Gauging {applies=tooling}

## Component Marking

All System tooling, fixtures, and gauges supplied by Provider must be identified with a permanently attached metal tag or engraving with the following information:

- Tool Number/Fixture Number/Gauge Number (To be supplied by the Consumer)
- Part number(s) or part family(ies) to which it applies
- If gauge, upper and lower tolerance limits.
- "Property of {company}"

# Available Utilities {kind=information}

## Electrical {kind=information}

The {plant} plant has {power_available} electrical power available.

## Pneumatic {kind=information}

The {plant} plant has plant-wide compressed air, supplied at {air_pressure}. The compressed air shall be regulated down to fit design parameters.

## Miscellaneous {kind=information}

The {plant} plant has {other_utilities}.

# Documentation

## Mechanical

Drawing package shall include but not be limited to:

- Index shall be first sheet
- All main level, mid-level and sub-level assembly drawings
  - Assembly drawings shall also include bill of materials in table format for all equipment shown on the assembly.
- Drawings to contain dimensional information required for debug, maintenance, equipment set-up, System install, etc.
- Manufacturing grade prints of any item that is deemed a spare or expendable wear part.

## Electrical

Drawing package shall include but not be limited to:

- Index shall be first sheet.
- System Interconnection Diagrams: Drawing shall show relative location and identifies all E-Stops, Fence Switches, Perimeter Guard switches, electrical boxes, and the cable and conduit runs. All cable and conduit runs should be labeled. Diagram shall also include bill of materials in table format for all devices shown on the diagram.
- Conduit Schedules and Pin Charts: Drawing shall show the conductor numbers or pin numbers for all cable and conduits runs. Drawings and charts shall also include bill of materials in table format for all devices shown on the drawings and/or charts
- I/O Drawings: Drawing shall show all inputs, outputs, dipswitch settings, settings definition, channel configuration, etc.
- Interface Drawings: Drawing shall show all hardware, dipswitch settings, setting definition, IP ad-dresses, and memory maps for interface between System and robots, drives, A-B Integrated Display Computer, Ignition, DeviceNet, Ethernet IP, etc.
- Panel Layouts: Drawing shall show, to scale, panel layouts and push-button layouts.

## Controls

Controls package shall include but not be limited to one (1) printed copy and a digital media copy for each of

- PLC program logic with cross reference
- Ignition (or other HMI) application files
- Ethernet/IP (or other network) application file
- Robot/CNC/Laser/Brake/etc programs
- Drives configuration file (if required)

## Miscellaneous

Sub-systems not covered above, such as Hydraulic, Pneumatic, Lubrication, etc in addition to any interconnections of sub-systems shall have documentation packages including but not limited to:

- Index shall be first sheet.
- Drawing shall show in schematic/symbol format all the valves, filters, regulators, flow switches, cylinders, proximity switches, limit switches, etc in relative position to the equipment.
- Diagram shall include bill of materials in table format for all devices shown on the diagram.
- Drawing shall show, to scale, panel layouts and push button layouts.

## System User Manuals

All manuals and documentation are to be provided to the Consumer in an electronic format. Hard copy manuals are not required.

Manuals will contain, but are not limited to, the following information:

- Operating instructions
- Set-up instructions
- System Sequence of Operations
  - Sequence step number
  - Description of sequence step
  - Valve, device, or switch made/energized (and its address)
  - Timing chart
- Preventative maintenance procedures
- Equipment troubleshooting guidelines
- Recommended spare parts list with cost/availability
- Catalogs, user manuals on major machine components
- Mechanical assembly drawings with BOM
- Spare part manufacturing prints
- Electrical and pneumatic schematic diagrams
- PLC program logic and cross reference

## System Layout

Showing size and general outline of overall System, including: existing machinery, location of loading and unloading areas, robot(s) location(s), safety fencing and access door swings, control panel access with door swings, operator position and location of service connections.

## Preventative Maintenance

The Provider shall supply a recommended schedule of preventative maintenance, with the task elements, recommended frequency, and consumable supplies, parts or tooling required.

# Project Milestones, Approvals, and Payment Schedule {kind=instruction}

The project will progress through the milestones described below, with the required Consumer approvals described, and resulting payments established. The Provider shall propose their percentage payment terms due with each milestone. [!Specifics determined at time of quotation]

- Quote
  - Provider will complete a quotation which satisfies the specifications laid out herein and present it to the Consumer for review. Revisions will be requested as necessary.
- Purchase Order
  - The Consumer will pay an initial down-payment after issuance of PO and receipt of invoice based on mutual agreement of all criteria and terms in this document, the URS Response Form, Providers quotation and any other written agreements.
- Design Review and Approval
  - The Consumer requires a design review and approval of the design prior to construction. It may be conducted in-person or via web conference. The Consumer requires review of the proposed design, mechanical general arrangement drawing(s), machine features and key parameters, and proposed HMI screens and description of control Systems functionality as applicable.
  - Documentation and drawings of the following types are required to be supplied at or before construction is begun. Approval of drawings does not relieve the vendor of responsibility for satisfactory performance of the equipment. Drawing numbers will be assigned with approval of drawings.
    - Machine layout
    - Tool and fixture layout
    - Perishable tools
    - Control drawings
  - Approval drawings must have final approval before equipment is built with all engineering changes completed. After final approval the System is considered to be under Design Freeze and any changes must be submitted to the Consumer for evaluation and approval.
- Factory Acceptance Testing
  - The Consumer will pay a third payment upon successful completion of the FAT as described below and/or agreed upon in writing.
  - The Consumer will visit the Provider's plant to complete initial training (if required) and to complete the FAT. The FAT will be conducted and documented on an FAT document to be provided and agreed upon in advance.
  - FAT will include: [!Specifics determined at time of quotation]
    - Review of the Consumer's machine safety checklist, to be provided in advance.
    - Inspection and verification of all design and construction features, functionality, materials and components, documentation as specified in this document, the deviations/corrections form, the Provider's quotation, previously approved drawings, HMI screens and any other written agreement.
    - Cyclic dry run of minimum 24 hours will be performed.
    - Trial runs of a minimum quantity of one (1) shift of product will be ran through the System for verification of functionality and repeatability.
  - If the FAT does not meet all the requirements described in this procedure and URS, then the Consumer may: reject the equipment and provide a written list of corrections/improvements to be completed prior to a repeat FAT; accept the equipment with improvements to be made either before shipment or before the time of the start-up and site validation at the {plant} plant; or accept the equipment as is.
- Site Acceptance Testing
  - The Consumer will pay the remaining amount due, after successful completion of installation and commissioning in the {plant} plant, start-up, validation, and receipt of any final documentation, drawings, software, etc. that are described in this document or agreed upon in writing.
  - Provider will install the System and complete any training (if required) at the Consumer's facility. The SAT will be conducted and documented on an SAT document to be provided in advance.
  - SAT will include: [!Specifics determined at time of quotation]
    - Inspection of all features to ensure no damages were incurred during disassembly, transport, and reassembly.
    - SAT Validation will include a repeat of the elements of the FAT in addition to the below items
    - Completion of the Consumer's machine safety checklist for the machine now in its final state and in its final location.
    - Verification that the appropriate plant utilities are connected appropriately.
    - Establishment of required preventative maintenance schedules and instructions.
    - Establishment of required spare parts, consumables and tooling.
    - Storage of manufacturer's documentation such as operating and maintenance manuals, drawings, bills-of-materials, spare parts lists, component cut sheets, etc.
- Crating, Insurance, and Shipment
  - Crating
    - Protection of the equipment during shipment is critical to both parties. Crating needs will depend on the risks of damage and on the method and distance of shipment.
  - Insurance
    - Insurance of the shipment is necessary to protect both parties. Appropriate levels of insurance will be determined before contract agreement
  - Shipment
    - The Provider shall describe the planned skidding/crating/protection, insurance and method of shipment in the quotation.
- Additional Support
  - If any additional support (not included in any warranty, maintenance, or service agreements) is determined to be necessary it will be contracted separately from this agreement.

# On-going Support {kind=instruction}

The Provider shall supply a description of:

- Their technical support and field service engineer resources
- Their base location(s)
- Expected response time both by phone for remote troubleshooting and assistance, as well as for on-site visit for break-down repairs and for scheduled routine maintenance
- Costs for unplanned break-down support
- Costs for an emergency service agreement plan

# Design and Document Ownership

During the warranty period (if one exists) any desired changes to any part of the provided System must be proposed and approved in writing by both Consumer and Provider.

The Consumer will become sole owner of all physical Systems, software Systems, and documentation of said Systems encompassed by this specification after the expiration of the warranty period (if one exists).

This includes but is not limited to:

- Mechanical Systems
- Electrical Systems
- Pneumatic Systems
- Hydraulic Systems
- Controls Systems
  - Controller (PLC, FPGA, etc.)
  - HMI
  - Robot
  - Servo
- Software
- Firmware
- etc.

All System documentation shall be provided in the following formats:

- All 2D CAD models in DXF or DWG formats
- All 3D CAD models in SolidWorks solid model format. Step or IGES models are acceptable with prior approval.

# Disclaimer {kind=information}

## Content {kind=information}

The Consumer reserves the right to revise this document at any time before the issuance of a PO, in order to update content based on:

- Further discussions and/or scope updates internal to the Consumer
- Updates from Providers Deviation Requests approved by the Consumer
- Typographical errors
- Missing, redundant, conflicting or non-applicable content
- Additions and/or subtractions to URS requirements

## Validity {kind=information}

Only the latest version of this document contains the applicable information that is to be used for procurement of the equipment, milestone payments adherence or any other requirement to be in consideration for this project.

# URS & RFQ Acknowledgement and Acceptance {kind=instruction pagebreak}

Please retain a copy of this sheet in your files and return an original signed copy, indicating that you have received, reviewed and accepted in principle the contents of this document. URS Response Form shall be attached to this acknowledgement as necessary. All communications with respect to the contents of this URS/RFQ are to be addressed initially to {company} engineers. This is a controlled document and revisions will be sent to the name indicated.

## Provider Contact Information {unnumbered kind=information}

::form
Supplier Name
Address
City, State, Zip
Telephone
E-mail
::

## Provider Acceptance {unnumbered kind=information}

::form
Authorized Signature
Name and Title
Date
::

## Consumer Acceptance {unnumbered kind=information}

::form
Authorized Signature
Name and Title
Date
::

# Appendix: FAT/SAT Plan {kind=information applies=fatsat pagebreak}

## Introduction {kind=information}

This Plan defines the inspection, test, and acceptance criteria used to verify that the System, as supplied by the Provider, conforms to the requirements of the project URS/RFQ, the Provider's quotation, and the Consumer's purchase order. Factory Acceptance Testing (FAT) is performed at the Provider's facility prior to shipment. Site Acceptance Testing (SAT) is performed at the Consumer's facility following installation. Successful completion of each phase, with all deviations resolved or formally accepted, is required before the corresponding milestone payment is released.

## Reference Documents {kind=information}

- [URS/RFQ document, revision and date]
- [Provider's quotation, revision and date]
- [Approved mechanical, electrical, and controls package]
- [Applicable codes and standards: NEC, NFPA 79, OSHA, ANSI/RIA, etc.]

## Confidentiality

Test data, photographs, video, and any process-specific information generated during FAT or SAT are confidential and subject to the same terms as the project URS/RFQ and any executed CDA/NDA between the parties.

## Personnel

| **Role** | **Name** | **Responsibility** |
| --- | --- | --- |
| Provider Test Lead |  | Executes test plan, records results |
| Consumer Engineering Witness |  | Verifies results against URS, approves/rejects |
| Consumer EHS Witness |  | Verifies safety compliance |
| Consumer Quality Witness |  | Verifies metrology and acceptance criteria |

## Documentation Review

The following must be available and reviewed before testing begins. Items not yet finalized should be flagged rather than blocking the start of testing, at the discretion of the Consumer.

- Approved mechanical drawings and bill of materials
- Approved electrical schematics and panel layouts
- PLC and HMI program backups
- Risk assessment / machine safety checklist
- Calibration certificates for all measurement devices used in testing

## Safety Review

Before energizing or operating the System, the Provider and Consumer EHS Witness shall walk the System to confirm guarding is in place, e-stops are accessible and functional, and all stored energy hazards are identified. No functional testing proceeds until this review is signed off.

| **Item** | **Verified (Y/N) – Witness Initials** |
| --- | --- |
| Guarding installed and secured |  |
| E-stops located, labeled, functional |  |
| Lockout/tagout points identified |  |
| Pinch points reviewed |  |

## Factory Acceptance Testing

### Mechanical Inspection

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| Construction matches approved drawings | No unapproved deviations |  |
| Surface finish / cosmetic condition | Per print, no damage |  |
| Fasteners torqued and secured | Per assembly spec |  |
| Guards, covers, panels fit and secure | No gaps, no sharp edges |  |
| [Add system-specific mechanical checks] |  |  |

### Electrical Inspection

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| Panel construction per Common Electrical Standards | NEMA rating, wire color, labeling |  |
| Wire numbering matches schematic | 100% traceable |  |
| Grounding and bonding verified | Continuity confirmed |  |
| Single point disconnect functions correctly | Disconnects all power |  |
| [Add system-specific electrical checks] |  |  |

### Pneumatic/Hydraulic Inspection

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| Operating pressure within spec | Per URS utility requirements |  |
| Shut-off valve, lockable, functions | Isolates and bleeds pressure |  |
| No audible or visible leaks at fittings | Zero leaks under pressure |  |
| Filters/regulators/lubricators installed per spec | Per pneumatic/hydraulic spec section |  |

### Controls and Software Verification

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| PLC I/O matches I/O drawing | 100% match |  |
| HMI screens match approved layout | Functions as designed |  |
| Access levels (Operator/Maintenance/Admin) function correctly | Password protected, correct permissions per level |  |
| Alarms trigger and clear correctly | All alarms tested individually |  |
| Recipe creation, save, load, edit functions | Matches URS recipe requirements |  |
| Backup copy of final software obtained | PLC, HMI, and any drive/robot programs |  |

### Safety System Verification

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| Each e-stop tested individually | Removes power/motion immediately |  |
| Guard interlocks tested individually | Machine stops when guard opened |  |
| Presence-sensing device (light curtain, etc.) tested | Stops machine per calculated safety distance |  |
| No auto-restart after power loss | Requires manual reset |  |
| Noise level measured at operator position | ≤ {noise_limit}, or per agreed limit |  |

### Functional and Process Verification

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| Manual mode operation | Each station/function operable independently |  |
| Automatic mode, single cycle | Completes full cycle without fault |  |
| Sequence of operations matches URS Process Flow | Step order and logic correct |  |
| Fault recovery (jam, fault, restart) | Recovers per design intent without damage |  |
| Reject/non-conforming part handling | Routed and identified per URS |  |

### Measurement System/Metrology Verification

Any measurement device used to determine pass/fail of product must be calibrated against a traceable standard and demonstrate adequate repeatability before use in production.

| **Measurement Type** | **Example Parameter** | **Acceptance Criteria** | **Reference Standard** |
| --- | --- | --- | --- |
| Dimensional | Critical dimension per print | ± [tolerance] | Calibrated gauge/CMM, cert # [ ] |
| Leak/seal integrity | Leak rate (pressure or vacuum decay) | ≤ [X] sccm or equivalent | NIST-traceable leak standard |
| Weight/mass | Net weight | ± [X]% of target | Calibrated test weights, cert # [ ] |
| Torque | Applied torque | ± [X]% of target | Calibrated torque analyzer |
| Vision/inspection | False accept / false reject rate | ≤ [X]% each | Known good/bad sample set, qty [ ] each |
| Temperature | Process or product temperature | ± [X]°F/°C | Calibrated reference thermometer |
| Pressure | Process pressure | ± [X] psi | Calibrated reference gauge |
| Force | Applied or resisting force | ± [X]% of target | Calibrated load cell |
| Flow | Flow rate | ± [X]% of target | Calibrated flow meter |
| Electrical continuity/resistance | Resistance or hipot result | Per applicable standard | Calibrated meter, cert # [ ] |

**Repeatability/Reproducibility (Gage R&R)**

For any measurement used as a pass/fail gate, a short study comparing repeated measurements of the same part (and, where applicable, measurements by more than one operator) should be performed and recorded, with results meeting an agreed minimum acceptable percentage of total variation.

**Correlation Study**

Where applicable, the System's measurement result should be checked against a set of known reference parts (good and bad) supplied by the Consumer, to confirm the System correctly distinguishes passing from failing product.

### Performance and KPI Verification

| **KPI** | **Target** | **Measured** | **Pass/Fail** |
| --- | --- | --- | --- |
| Cycle time | [X] sec/part |  |  |
| Throughput / TAKT time | [X] parts/hr |  |  |
| First pass yield | ≥ [X]% |  |  |
| False reject rate | ≤ [X]% |  |  |
| False accept rate | ≤ [X]% |  |  |
| Uptime/availability during extended run | ≥ [X]% |  |  |
| Mean time between faults (extended run) | ≥ [X] hours |  |  |
| Changeover time | ≤ [X] min |  |  |
| Scrap/defect rate | ≤ [X]% |  |  |

### Extended Run/Dry Run

A cyclic dry run of a minimum of [X] hours shall be performed without product, followed by a trial run of a minimum of [X] units/shifts of actual or representative product, to verify functionality, repeatability, and the performance metrics above under sustained operation.

| **Run Type** | **Duration/Quantity** | **Faults Observed** | **Pass/Fail** |
| --- | --- | --- | --- |
| Dry run (no product) | [X] hours |  |  |
| Trial run (with product) | [X] units |  |  |

### Deviations & Punch List

Severity definitions: **Critical** (must resolve before shipment), **Major** (must resolve before SAT), **Minor** (may resolve during or after SAT by agreement).

| **Item #** | **Description** | **Severity** | **Responsible Party** | **Target Resolution Date** | **Status** |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |

### FAT Acceptance and Sign-off

By signing below, the Consumer acknowledges that FAT has been completed, that all Critical and Major items in the punch list above have been resolved or formally accepted with a documented resolution plan, and that the System is approved for shipment.

::form
Consumer Signature | Date
Provider Signature | Date
::

### Deviation and Corrective Action Log

Consolidated tracking of all open items from FAT through final closure.

| **Item #** | **Description** | **Resolution** | **Closed Date** | **Closed By** |
| --- | --- | --- | --- | --- |
| 1 |  |  |  |  |
| 2 |  |  |  |  |

## Site Acceptance Testing

### Transport and Receiving Inspection

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| No visible shipping damage | Visual inspection on arrival |  |
| All crated items accounted for | Matches packing list |  |
| No loosened fasteners/components from transit | Visual and functional check |  |

### Installation and Utility Connection Verification

| **Item** | **Acceptance Criteria** | **Result/Comments** |
| --- | --- | --- |
| System leveled and anchored per drawing | Per installation drawing |  |
| Electrical service connected and verified | Correct voltage, phase, rotation |  |
| Pneumatic/hydraulic service connected and verified | Correct pressure, no leaks |  |
| Network/data connections established | Per interface drawing |  |
| Safety devices reconnected and tested in final location | Same tests as FAT Section 16.7.5 |  |

### Safety System Verification

Repeat the relevant checks from FAT Sections 16.7.4-16.7.6 in the System's final installed location and configuration. Reference the FAT results; only deviations from FAT performance need be detailed here.

| **Item** | **FAT Result Reference** | **SAT Result** | **Pass/Fail** |
| --- | --- | --- | --- |
| Controls/software functions | Section 16.7.4 |  |  |
| Safety systems | Section 16.7.5 |  |  |
| Functional/process sequence | Section 16.7.6 |  |  |

### Measurement System/Metrology Verification

Repeat applicable rows from Section 16.7.7 at the installed location to confirm no degradation occurred during transport and reinstallation, and that local environmental conditions (vibration, ambient temperature, electrical noise) do not affect measurement performance.

### Production Trial Run

| **Run Type** | **Duration/Quantity** | **Faults Observed** | **Pass/Fail** |
| --- | --- | --- | --- |
| Production trial (with actual product, actual operators) | [X] units / [X] shifts |  |  |

### Deviations & Punch List

| **Item #** | **Description** | **Severity** | **Responsible Party** | **Target Resolution Date** | **Status** |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |

### Preventative Maintenance, Spares, and Documentation Handoff

| **Item** | **Status** |
| --- | --- |
| Preventative maintenance schedule provided |  |
| Recommended spare parts list provided |  |
| As-built mechanical, electrical, and controls documentation provided |  |
| Operator and maintenance training completed |  |
| Software/firmware backup copies delivered to Consumer |  |

### SAT Acceptance and Sign-off

By signing below, the Consumer acknowledges that SAT has been completed, that all Critical and Major items have been resolved or formally accepted with a documented resolution plan, and that the System is accepted into service.

::form
Consumer Signature | Date
Provider Signature | Date
::

### Deviation and Corrective Action Log

Consolidated tracking of all open items from SAT through final closure.

| **Item #** | **Description** | **Resolution** | **Closed Date** | **Closed By** |
| --- | --- | --- | --- | --- |
| 1 |  |  |  |  |
| 2 |  |  |  |  |

## Final Acceptance {kind=information}

This section is completed once all items in FAT and SAT sections are closed and the System is fully accepted by the Consumer.

**Provider Contact Information**

::form
Supplier Name
Address
City, State, Zip
Telephone
E-mail
::

**Provider Acceptance**

::form
Authorized Signature
Name and Title
Date
::

**Consumer Acceptance**

::form
Authorized Signature
Name and Title
Date
::
