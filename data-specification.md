# Data Specification — Torque Specification Files

## Overview

These XML files contain torque specifications for automotive fasteners. They are used in workshop documentation systems to look up the correct torque value for a given part.

## Filename Convention

Filenames encode metadata about the part:

```
{Manufacturer}-{Manufacturer}-{ManufacturerCode}{MainGroup}{SubGroup}-{Series}_{Variant}.xml
```

Example: `AZD-AZD-AZDMUC4161-F01_RBU.xml` → Manufacturer AZD, main group 41, sub group 61, series F01.

## XML Structure

Each file contains a `<TorqueDocument>` with a list of `<Address>` entries. Each address represents a torque specification for a specific part/location, identified by a code, with a validity date range.

Torque values are in Newton-metres (Nm) and may use European decimal notation (comma as decimal separator).

## Data Quality

Production data may contain quality issues. Your validators should catch anything that would be problematic for a workshop technician relying on this data.
