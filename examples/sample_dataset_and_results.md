# Sample dataset & analysis results

Standalone reference: the dataset AutoAnalyst AI analyzed, and the full
results it produced, for the prompt *"Summarize the dataset and highlight
data quality issues."*

## Sample dataset

| Field | Value |
|---|---|
| File | `sales_customer_dataset.csv` (CSV) |
| Rows × Columns | 500 × 28 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Numeric columns | `Customer_Age`, `Quantity`, `Unit_Price`, `Discount_Percent`, `Gross_Sales`, `Discount_Amount`, `Net_Sales`, `Cost`, `Profit`, `Profit_Margin_Percent`, `Customer_Satisfaction`, `Returned` |
| Categorical columns | `Order_ID`, `Customer_ID`, `Customer_Name`, `Gender`, `City`, `State`, `Region`, `Customer_Segment`, `Sales_Channel`, `Product_Category`, `Product_Subcategory`, `Payment_Method`, `Salesperson`, `Loyalty_Member` |
| Date columns | `Order_Date`, `Ship_Date` |

## Results

### Executive summary

The dataset comprises 500 rows and 28 columns, providing a detailed view of
sales transactions. It is complete with no missing or duplicate values,
indicating high data integrity. However, there are data quality concerns,
including unexpected values in the `Gender` column and outliers in several
numeric columns, which may affect the reliability of the analysis.

### Analysis plan (6 steps, all completed)

1. **Provide an overview of the dataset's structure and basic statistics** — `df.head()` and `df.describe()` for basic statistics on numeric columns.
2. **Identify potential data quality issues related to missing values** — `df.isnull().sum()`, confirming no missing values.
3. **Detect any duplicate rows in the dataset** — `df.duplicated().sum()`, confirming no duplicate rows.
4. **Identify any unusual or unexpected values in categorical columns** — `value_counts()` on categorical columns such as `Gender`, surfacing an unexpected `Other` category.
5. **Identify outliers in numeric columns** — box plots for `Unit_Price`, `Gross_Sales`, and `Profit` via matplotlib.
6. **Summarize data quality issues found** — compiled the findings and recommendations below.

### Key findings

- The dataset is complete with no missing values across all columns. *(Total missing values: 0)*
- There are no duplicate rows in the dataset. *(Duplicate rows count: 0)*
- Unexpected value `Other` found in the `Gender` column. *(Gender unique values: 3, top: `Other`, freq: 174)*
- Outliers detected in numeric columns such as `Gross_Sales`, `Discount_Amount`, and `Profit`. *(Gross_Sales max: 35678.1, Discount_Amount max: 6936.52, Profit max: 12968.3)*

### Charts

**Data quality**

![Missing values by column](charts/step2_missing_values.png)

**Categorical column distributions**

![City value counts](charts/step4_City_value_counts.png)
![Customer ID value counts](charts/step4_Customer_ID_value_counts.png)
![Customer Name value counts](charts/step4_Customer_Name_value_counts.png)
![Customer Segment value counts](charts/step4_Customer_Segment_value_counts.png)
![Gender value counts](charts/step4_Gender_value_counts.png)
![Loyalty Member value counts](charts/step4_Loyalty_Member_value_counts.png)
![Order ID value counts](charts/step4_Order_ID_value_counts.png)
![Payment Method value counts](charts/step4_Payment_Method_value_counts.png)
![Product Category value counts](charts/step4_Product_Category_value_counts.png)
![Product Subcategory value counts](charts/step4_Product_Subcategory_value_counts.png)
![Region value counts](charts/step4_Region_value_counts.png)
![Sales Channel value counts](charts/step4_Sales_Channel_value_counts.png)
![Salesperson value counts](charts/step4_Salesperson_value_counts.png)
![State value counts](charts/step4_State_value_counts.png)

**Outlier detection**

![Gross Sales boxplot](charts/step5_Gross_Sales_boxplot.png)
![Profit boxplot](charts/step5_Profit_boxplot.png)
![Unit Price boxplot](charts/step5_Unit_Price_boxplot.png)
![Unit price outliers](charts/step6_unit_price_outliers.png)

### Recommendations

- Investigate and address the unexpected `Other` value in the `Gender` column to ensure data accuracy.
- Review and potentially adjust outliers in numeric columns to prevent skewed analysis results.

### Limitations

- The dataset includes future dates (2025), which may not align with current data trends.
- Presence of outliers in several numeric columns could skew analysis results if not addressed.
