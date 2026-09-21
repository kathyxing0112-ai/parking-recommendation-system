# Cornell Smart Parking Availability and Recommendation System

## Operational Concept

The Operational Concept describes a typical parking-recommendation scenario. A Cornell driver enters the destination, expected arrival and departure times, vehicle information, group size, and parking eligibility. The system obtains current parking availability, contextual information, and applicable parking policy constraints from external sources.

The system uses these inputs to evaluate eligible parking options, estimate their availability, and rank the most suitable alternatives. It then provides the recommended locations, expected availability, and supporting information to the driver. The driver reviews the results and chooses an option based on the trip needs.

The system provides decision support only. It does not reserve parking spaces or control physical parking operations.

   ## Running the Application

```bash
   python app.py
```

At this increment, the command runs one end-to-end UC.1 walking-skeleton
scenario and prints a hard-coded, synthetic ranked parking recommendation.
No real parking data source, ranking algorithm, or language model is used.