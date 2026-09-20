# System Context

## System of Interest

The System of Interest (SoI) is the Cornell Smart Parking Availability and Recommendation System. It is a web-based decision-support system that provides parking information and recommendations based on available parking data and user constraints.

## System Boundary

The system boundary includes functions directly performed by the smart parking platform. These functions include:

- Receiving driver information
- Accessing parking information
- Evaluating parking options
- Considering user constraints
- Estimating parking availability
- Generating ranked parking recommendations
- Presenting recommendations to the driver

The following activities are outside the system boundary:

- Physical parking operations
- Parking enforcement
- Physical allocation of parking spaces
- Reservation of parking spaces
- Direct control of parking facilities

The system provides decision support only.

## External Context Elements and Boundary Interactions

### X.C.1 Cornell Driver

- Role: Primary user of the system
- Direction: Bidirectional
- Information entering the SoI:
  - Destination
  - Expected arrival time
  - Expected departure time
  - Vehicle information or vehicle type
  - Group size
  - Parking eligibility
  - Parking request
- Information leaving the SoI:
  - Ranked parking recommendations
  - Expected parking availability
  - Supporting parking information
- Interface form: Web-based user input and displayed recommendations

### X.C.2 Parking Availability Data Sources

- Role: Provides parking availability information used by the system
- Direction: Primarily into the SoI
- Information entering the SoI:
  - Current parking availability data
  - Historical parking information, when available
- Information leaving the SoI:
  - Parking-data request, if required by the data source
- Interface form: Not yet specified in the current model or report
- Interface name: Parking Availability Data Interface

### X.C.3 Contextual Information Sources

- Role: Provides contextual information used to evaluate parking options
- Direction: Primarily into the SoI
- Information entering the SoI:
  - Relevant contextual information
  - Environmental or trip-related context
- Information leaving the SoI:
  - Context-data request, if required by the source
- Interface form: Not yet specified in the current model or report
- Interface name: Context Data Interface

### X.C.4 Cornell Transportation and Parking Services

- Role: Provides parking policies, rules, eligibility requirements, and operational information
- Direction: Primarily into the SoI
- Information entering the SoI:
  - Parking policy constraints
  - Parking rules
  - Parking eligibility information
  - Relevant operational information
- Information leaving the SoI:
  - Policy-information request, if required by the source
- Interface form: Not yet specified in the current model or report
- Interface name: Parking Policy Interface

### X.C.5 Cloud and Network Infrastructure

- Role: Enabling system that supports hosting, network access, operation, and maintenance
- Direction: Bidirectional
- Information or services crossing the boundary:
  - Application hosting support
  - Network communication
  - Technical infrastructure services
  - Supporting system data
- Interface form: Cloud and network services; specific technology is not yet defined
- Interface name: Hosting and Network Interface

### ENV.C.1 Cornell Campus Parking Environment

- Role: Defines the physical and operational environment in which the system operates
- Direction: Contextual relationship with the SoI
- Context provided:
  - Cornell parking facilities
  - Campus transportation conditions
  - Parking operations
  - Surrounding travel conditions
- Direct data interface: No direct data interface is currently specified
- Relationship name: Campus Environment Context

## Boundary Rationale

The system boundary focuses on functions directly responsible for providing parking decision support. Physical parking operations and enforcement remain outside the boundary because the system provides information and recommendations but does not directly control parking facilities or parking spaces.

## Current Interface Limitations

The current system model identifies the logical information crossing each boundary, but it does not yet define the detailed technical interface formats for all external sources. Items such as API protocols, JSON schemas, authentication methods, update frequencies, and error behavior will be specified in later system-development activities.