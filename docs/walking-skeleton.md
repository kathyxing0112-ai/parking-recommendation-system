# Walking Skeleton — UC.1 Find Suitable Parking

This increment builds the walking skeleton for UC.1, the single use case that
delivers the main value of the system-of-interest: a Cornell Driver obtaining
ranked parking recommendations for a planned trip.

## Sequence (from the model, verb-oriented)

1.  Cornell Driver -> Cornell Driver Interface: submit trip request
2.  Cornell Driver Interface -> Smart Parking Service: forward trip request
3.  Smart Parking Service -> Parking Availability Data Sources: request current parking availability
4.  Parking Availability Data Sources -> Smart Parking Service: return current parking availability
5.  Smart Parking Service -> Contextual Information Sources: request contextual information
6.  Contextual Information Sources -> Smart Parking Service: return contextual information
7.  Smart Parking Service -> Cornell Transportation and Parking Services: request parking policy constraints
8.  Cornell Transportation and Parking Services -> Smart Parking Service: return parking policy constraints
9.  Smart Parking Service -> Recommendation Model: request recommendation explanation
10. Recommendation Model -> Smart Parking Service: return recommendation explanation
11. Smart Parking Service -> Cornell Driver Interface: return ranked parking recommendations
12. Cornell Driver Interface -> Cornell Driver: display ranked parking recommendations

## Participants

The system context diagram represents the Smart Parking System (C.0) as a
single system-of-interest. This call list is finer-grained: it names the
minimum internal components required to carry one driver action across every
boundary the context diagram shows.

### External actors and systems

- Cornell Driver (X.C.1) — a person; the system's interface to this actor is
  `cornell_driver_interface/`
- Parking Availability Data Sources (X.C.2) — `parking_availability_data_sources/`
- Contextual Information Sources (X.C.3) — `contextual_information_sources/`
- Cornell Transportation and Parking Services (X.C.4) — `cornell_transportation_and_parking_services/`

### Components internal to the system-of-interest

- Cornell Driver Interface — `cornell_driver_interface/`
- Smart Parking Service — `smart_parking_service/`
- Recommendation Model — `recommendation_model/`

The Smart Parking Service coordinates the end-to-end request. The
Recommendation Model stands in for the local language model recorded in
`docs/adr/0001-initial-toolchain.md`; because that decision runs the model
locally, it sits inside the system boundary rather than outside it.

These three components are not external systems, so they do not appear on the
system context diagram, the Universe hierarchy, or the use case diagram, and
they need no lifeline of their own in the sequence diagram, which shows
interactions between actors rather than actions internal to one. The
system-of-interest is modeled as a single asset at this stage; decomposing it
into named subsystems is later work. What must agree between the model and this
call list is the set of external participants, the message names, and their
order.

Cloud and Network Infrastructure (X.C.5) is an enabling system. It supports
future hosting and network access but is not invoked by the UC.1 walking
skeleton. Its Chapter 1 placeholder package remains unchanged.

## Stub rule

Every response above is a hard-coded value of the right shape and type. The
values are synthetic and do not represent real Cornell parking data.

No real parking-data query, no real language-model call, no filtering, no
ranking algorithm, no error handling, no retries, and no logging appear in this
increment. None of that is specified yet; those behaviors wait for the
functional requirements developed in later chapters.
