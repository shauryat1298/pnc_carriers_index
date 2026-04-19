# P&C Market Share PDF Structure

Source file: `artifacts/publication-msr-pb-property-casualty.pdf`

Report identified from the PDF as: **2024 Market Share Reports for Property/Casualty Groups and Companies by State and Countrywide**.

The PDF is a 707-page NAIC property/casualty market share report. Its core data is not presented as one flat table; it is organized into repeated report sections by line of business, with countrywide rankings first and then state/jurisdiction rankings.

## Document-Level Structure

1. Cover / NAIC publication front matter
2. Table of contents
3. Introduction
4. Property/Casualty Market Share Report Applications
5. Direct loss ratio tables by line of business
6. Direct written premium trend graph, 2015-2024
7. 2024 market share reports by line of business
8. Technical notes
9. Index of insurer groups and companies

## Front Matter

### Introduction

The introduction explains the purpose and scope of the report:

- It covers property/casualty market share information by group/company.
- Market share is based on direct written premium.
- It includes 33 lines of business, plus aggregate write-ins for other lines and total all lines.
- State-level sections are limited to the top 10 groups/companies.
- Countrywide sections show the top 125 groups/companies.
- The countrywide views are provided both including and excluding Canada and other alien data.
- Accident and health market share lines are excluded from this P/C report.
- Insurance groups are based on group structures filed with NAIC as of the report generation date.
- An index at the end maps groups to affiliated companies and lists unaffiliated companies.

### Market Share Report Applications

This section describes use cases for the data:

- Assess competitive position.
- Create benchmarks.
- Identify top writers.
- Analyze overall market size.
- Identify premium volume trends.
- Evaluate market penetration potential.
- Evaluate post-merger market implications.

### Direct Loss Ratio by Line of Business

Before the line-by-line market share tables, the report contains direct loss ratio summary tables.

Structure:

- Scope: States, U.S. territories, Canada, and Aggregate Other Alien.
- Unit: In millions.
- Rows: Lines of business.
- Columns repeat by year for 2024, 2023, 2022, 2021, and 2020.
- Each year has earned direct premium, losses, and loss ratio.
- Loss ratio formula shown in the report: incurred losses / earned premiums * 100.

### Direct Written Premium Trend Graph

The report includes a chart titled **Direct Written Premium Trend, 2015-2024**.

The graph shows:

- Direct written premium in billions.
- Growth rate percentage.
- Years 2015 through 2024.

## Repeated Market Share Section Pattern

Each line-of-business section follows the same general structure.

### Geographic Blocks

For each line of business, the report presents:

1. **Countrywide Top 125 including Canada and Other Alien**
   - Header appears as: `STATES, U.S. TERRITORIES, CANADA, AGGREGATE OTHER ALIEN`
   - Ranked top 125 groups/companies.

2. **Countrywide Top 125 excluding Canada and Other Alien**
   - Header appears as: `STATES AND U.S. TERRITORIES`
   - Ranked top 125 groups/companies.

3. **Top 10 by State / Jurisdiction**
   - Header appears as: `BY STATE BY GROUP`
   - Top 10 groups/companies for each state or jurisdiction.
   - Includes state total rows.

### Table Columns

The main market-share tables use this column pattern:

- Rank
- Group/Company Code
- Group/Company Name
- State or jurisdiction name, when in state-level block
- Direct Written Premiums, in thousands
- Direct Earned Premiums, in thousands
- Market Share
- Cumulative Market Share
- Loss Ratio
- Loss & Cost Containment Ratio

The row grain is generally:

```text
line_of_business + geography_scope + jurisdiction_if_applicable + ranked_group_or_company
```

For state-level blocks, each jurisdiction has up to 10 ranked rows, followed by a `STATE TOTAL` row.

## Lines of Business Present

The main market-share sections begin around report page 9 and are ordered as follows:

| Report page | Line number | Line of business |
|---:|---|---|
| 9 | 35 | Total All Lines |
| 29 | 01 | Fire |
| 49 | 02.1 | Allied Lines |
| 69 | 02.2 | Multiple Peril Crop |
| 83/84 | 02.3 | Federal Flood |
| 100 | 02.4 | Private Crop |
| 112/113 | 02.5 | Private Flood |
| 131/132 | 03 | Farmowners Multiple Peril |
| 149/150 | 04 | Homeowners Multiple Peril |
| 168/169 | 05 | Total Commercial Multiple Peril |
| 187/189 | 06 | Mortgage Guaranty |
| 201/203 | 08 | Ocean Marine |
| 221/223 | 09.1 | Inland Marine |
| 241/242 | 09.2 | Pet Insurance |
| 257 | 10 | Financial Guaranty |
| 267 | 11.1, 11.2 | Medical Professional Liability |
| 286 | 12 | Earthquake |
| 306 | 16 | Workers Compensation |
| 325 | 17.1, 17.2 | Other Liability |
| 345 | 17.3 | Excess Workers Compensation |
| 361 | 18.1, 18.2 | Products Liability |
| 380 | 19.1, 19.2 | Private Passenger Auto Liability |
| 399 | Derived total | Total Private Passenger Auto |
| 418 | 19.3, 19.4 | Commercial Auto Liability |
| 438 | Derived total | Total Commercial Auto |
| 458 | 21.1 | Private Passenger Auto Physical Damage |
| 477 | 21.2 | Commercial Auto Physical Damage |
| 496 | 22 | Aircraft, All Perils |
| 513 | 23 | Fidelity |
| 532/552 | 24 | Surety |
| 552/571 | 26 | Burglary and Theft |
| 571/572 | 27 | Boiler and Machinery |
| 590 | 28 | Credit |
| 607 | 30 | Warranty |
| 624 | 34 | Aggregate Write-ins for Other Lines of Business |

Note: page numbers above are report page labels extracted from the PDF text. A few starts show a one-page ambiguity because the PDF text extraction separates footer/page labels from table content; the table of contents and extracted page headers agree on the sequence.

## Index Section

The index begins after the technical notes, around report page 647.

It contains two major index structures:

### Companies Affiliated With a Group by Group Name

This maps insurer groups to their member companies.

Columns:

- Group Code
- Group Name
- Individual Company Code
- Company Name

### Companies Not Affiliated With a Group by Company Name

This lists standalone companies that are not part of a group.

Columns:

- Individual Company Code
- Company Name

## Data Modeling Notes

If this PDF is converted into a database or structured dataset, the natural entities are:

- Report metadata: report year, publication title, source PDF, page count.
- Line of business: line number, normalized line name, section start page.
- Geography scope: countrywide including Canada/Alien, countrywide U.S./territories only, state/jurisdiction.
- Jurisdiction: state, U.S. territory, Canada, Aggregate Other Alien, depending on block.
- Group/company: code, name, affiliation status.
- Market share row: rank, written premium, earned premium, market share, cumulative market share, loss ratio, loss and cost containment ratio.
- Group-company index: group code/name to individual company code/name.
- Unaffiliated company index: individual company code/name.

## Extraction Notes

The PDF is text-based, not purely scanned, but some embedded font mappings produce spacing artifacts in extracted text. The table structure, headings, line-of-business list, and column names are still recoverable.

