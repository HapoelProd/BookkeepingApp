"""
Hapoel Jerusalem Basketball - Bookkeeping Web Application
Professional local web platform for CSV processing
Based on your existing bookkeeping logic
"""
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import pandas as pd
import numpy as np
import sys

# Configuration
class Config:
    SECRET_KEY = 'hapoel-jerusalem-basketball-2025'
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if uploaded file is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class BookkeepingProcessor:
    """Your exact bookkeeping logic wrapped in a class"""

    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path
        self.df = None
        self.without_advertisement = None
        self.advertisment = None
        self.rest = None
        self.excel_summary = None
        self.new_filename = None
        self.output_path = None

    def load_data(self):
        """Load and prepare initial data"""
        self.df = pd.read_csv(self.csv_file_path)
        self.df['InstallmentDate'] = pd.to_datetime(
            self.df['InstallmentDate'],
            format='%d/%m/%Y',
            dayfirst=True
        )

        # Extract date range for filename
        min_date = self.df['InstallmentDate'].min()
        max_date = self.df['InstallmentDate'].max()
        start_date_str = min_date.strftime("%d.%m")
        end_date_str = max_date.strftime("%d.%m")

        self.new_filename = f"פקודת_יומן_{start_date_str}-{end_date_str}.xlsx"

    def split_data(self):
        """Split data by payment reference (exact logic from your script)"""
        # Split 79991 vs rest using forward-filled payment ref
        block_key = self.df['InstallmentPaymentExtRef'].replace({
            "": pd.NA, "nan": pd.NA, "NaN": pd.NA
        }).ffill()
        block_key = pd.to_numeric(block_key, errors="coerce").astype("Int64").astype(str)

        only_79991 = self.df[block_key == "79991"].copy()
        rest = self.df[block_key != "79991"].copy()

        # Within 79991, split segments that contain 4118
        code = pd.to_numeric(only_79991["InstallmentProductExtRef"], errors="coerce")
        only_79991["InstallmentProductExtRef"] = code

        seg_id = code.isna().cumsum()
        seg_has_4118 = (code == 4118).groupby(seg_id).transform("any")

        self.advertisment = only_79991[seg_has_4118].copy()
        self.without_advertisement = only_79991[~seg_has_4118].copy()

        # Fix 1: Drop rows where שם המוצר = "Other Payment" from rest
        # First apply column renaming to rest to get Hebrew column names
        self.rest = rest

    def prepare_columns(self):
        """Prepare columns with Hebrew names (exact logic from your script)"""
        # Drop unwanted columns
        columns_to_drop = ['Installment Ticket Id', 'InstallmentValueDate', 'Installments']

        for col in columns_to_drop:
            for df_obj in [self.without_advertisement, self.advertisment, self.rest]:
                if col in df_obj.columns:
                    df_obj.drop(columns=[col], inplace=True)

        # Column renaming
        column_mapping = {
            'InstallmentTransactionId': 'טרנזקציה',
            'InstallmentDate': 'תאריך העסקה',
            'InstallmentProducts': 'שם המוצר',
            'InstallmentPaymentPrice': 'חובה',
            "InstallmentProductPrice": 'זכות',
            "InstallmentPaymentExtRef": 'חשבון בחובה',
            "InstallmentProductExtRef": 'חשבון בזכות'
        }

        # Apply column renaming
        for df_obj in [self.without_advertisement, self.advertisment, self.rest]:
            df_obj.rename(columns=column_mapping, inplace=True)

        # Fix 1: Drop rows where שם המוצר = "Other Payment" from נתונים נוספים (rest)
        if 'שם המוצר' in self.rest.columns:
            initial_count = len(self.rest)
            self.rest = self.rest[self.rest['שם המוצר'] != 'Other Payment'].copy()
            # Reset the index after filtering
            self.rest = self.rest.reset_index(drop=True)
            filtered_count = len(self.rest)
            print(f"Debug: Filtered out {initial_count - filtered_count} 'Other Payment' rows from נתונים נוספים")

        # Format date columns to show only date without time
        for df_obj in [self.without_advertisement, self.advertisment, self.rest]:
            if 'תאריך העסקה' in df_obj.columns:
                print(f"Debug: Processing date column. Sample values: {df_obj['תאריך העסקה'].head()}")
                try:
                    df_obj['תאריך העסקה'] = pd.to_datetime(df_obj['תאריך העסקה'], errors='coerce').dt.strftime('%Y-%m-%d')
                    print(f"Debug: Date formatting successful")
                except Exception as e:
                    print(f"Debug: Date formatting error: {str(e)}")
                    raise e

        # Ensure all dataframes have same columns
        all_columns = self.without_advertisement.columns.tolist()
        self.advertisment = self.advertisment.reindex(columns=all_columns)
        self.rest = self.rest.reindex(columns=all_columns)

        # Add sequential numbers and command dates (after filtering)
        for df_obj in [self.without_advertisement, self.advertisment, self.rest]:
            # Remove any existing 'מס.סידורי' column first
            if 'מס.סידורי' in df_obj.columns:
                df_obj.drop(columns=['מס.סידורי'], inplace=True)
            df_obj.insert(0, 'מס.סידורי', range(1, len(df_obj) + 1))
            # Get the max date from the already formatted date column
            if 'תאריך העסקה' in df_obj.columns and len(df_obj) > 0:
                print(f"Debug: Processing command date. Sample transaction dates: {df_obj['תאריך העסקה'].head()}")
                try:
                    # Since we already converted to string, just use the max string value
                    max_date_str = df_obj['תאריך העסקה'].max() if not df_obj['תאריך העסקה'].isna().all() else ''
                    df_obj['תאריך פקודה'] = max_date_str
                    print(f"Debug: Command date set to: {max_date_str}")
                except Exception as e:
                    print(f"Debug: Command date error: {str(e)}")
                    raise e

    def create_excel_summary(self):
        """Create Excel format summary (exact logic from your script)"""
        # Get command date
        all_dates = []
        # Only use the 'rest' dataframe (נתונים נוספים) for summary
        dataframes_dict = {
            'rest': self.rest
        }

        for df in dataframes_dict.values():
            if len(df) > 0:
                all_dates.extend(df['תאריך העסקה'].tolist())

        # Since dates are already strings in YYYY-MM-DD format, convert to DD/MM/YYYY
        if all_dates:
            max_date_str = max(all_dates)  # This is already a string like "2025-11-27"
            if max_date_str and max_date_str != '':
                try:
                    # Convert from YYYY-MM-DD to DD/MM/YYYY
                    date_parts = max_date_str.split('-')
                    if len(date_parts) == 3:
                        command_date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
                    else:
                        command_date = max_date_str
                except:
                    command_date = max_date_str
            else:
                command_date = ''
        else:
            command_date = ''

        summary_rows = []

        # Summary structure
        summary_rows.append({
            'תאריך פקודה': '', 'חשבון חובה': '', 'חשבון זכות': '',
            'שם מוצר': '', 'סכום של חובה': '', 'סכום של זכות': ''
        })

        # Revenue entries from actual data
        revenue_summary = {}
        for sheet_name, df in dataframes_dict.items():
            if len(df) > 0:
                revenue_data = df[df['חשבון בזכות'].notna() & (df['זכות'] > 0)].groupby([
                    'חשבון בזכות', 'שם המוצר'
                ]).agg({'זכות': 'sum'}).reset_index()

                for _, row in revenue_data.iterrows():
                    account = row['חשבון בזכות']
                    product = row['שם המוצר']
                    amount = row['זכות']

                    if account in [70001, 70100]:
                        continue

                    key = (account, product)
                    if key not in revenue_summary:
                        revenue_summary[key] = 0
                    revenue_summary[key] += amount

        # Add revenue entries
        for (account, product), amount in revenue_summary.items():
            if amount > 0:
                summary_rows.append({
                    'תאריך פקודה': command_date,
                    'חשבון חובה': '',
                    'חשבון זכות': str(int(account)) if pd.notna(account) else '',
                    'שם מוצר': product,
                    'סכום של חובה': '',
                    'סכום של זכות': f"{amount:,.0f}".replace(',', ',')
                })

        # Totals
        total_debit = 0
        total_credit = sum(df['זכות'].sum() for df in dataframes_dict.values() if len(df) > 0)

        summary_rows.append({
            'תאריך פקודה': f'סה"כ {command_date}',
            'חשבון חובה': '',
            'חשבון זכות': 'סה"כ(זכות)',
            'שם מוצר': 'סכום כולל',
            'סכום של חובה': f"{total_debit:,.0f}",
            'סכום של זכות': f"{total_credit:,.0f}"
        })

        self.excel_summary = pd.DataFrame(summary_rows)

    def save_excel(self, output_dir='static/uploads'):
        """Save Excel file with all sheets"""
        os.makedirs(output_dir, exist_ok=True)
        self.output_path = os.path.join(output_dir, self.new_filename)

        # Create rest sheet name
        min_date = self.df['InstallmentDate'].min()
        max_date = self.df['InstallmentDate'].max()
        start_date_str = min_date.strftime("%d.%m")
        end_date_str = max_date.strftime("%d.%m")
        rest_sheet_name = f"פקודת יומן {start_date_str}-{end_date_str}.{max_date.year}"

        with pd.ExcelWriter(self.output_path, engine="openpyxl") as writer:
            self.without_advertisement.to_excel(writer, sheet_name="without_ad", index=False)
            self.advertisment.to_excel(writer, sheet_name="advertisement", index=False)
            self.rest.to_excel(writer, sheet_name=rest_sheet_name, index=False)
            self.excel_summary.to_excel(writer, sheet_name="Summary", index=False)

    def process(self):
        """Execute full processing pipeline"""
        self.load_data()
        self.split_data()
        self.prepare_columns()
        self.create_excel_summary()
        self.save_excel()

        return {
            'without_ad': self.without_advertisement,
            'advertisement': self.advertisment,
            'rest': self.rest,
            'summary': self.excel_summary,
            'filename': self.new_filename,
            'output_path': self.output_path
        }

    def get_balance_validation(self):
        """Get balance validation results with Hebrew names"""
        results = {}

        # Hebrew names mapping
        hebrew_names = {
            'without_ad': 'ללא פרסומים',
            'advertisement': 'פרסומים',
            'rest': 'נתונים נוספים'
        }

        for name, df in [('without_ad', self.without_advertisement),
                        ('advertisement', self.advertisment),
                        ('rest', self.rest)]:
            if df is not None and len(df) > 0:
                hebrew_name = hebrew_names[name]

                # Check transaction-level balance instead of sheet-level
                if 'טרנזקציה' in df.columns and 'חובה' in df.columns and 'זכות' in df.columns:
                    # Group by transaction and check balance for each transaction
                    transaction_balance = df.groupby('טרנזקציה').agg({
                        'חובה': 'sum',
                        'זכות': 'sum'
                    }).reset_index()

                    # Calculate difference for each transaction
                    transaction_balance['difference'] = transaction_balance['חובה'] - transaction_balance['זכות']

                    # For display purposes, only sum the imbalances from unbalanced transactions
                    unbalanced_transactions = transaction_balance[abs(transaction_balance['difference']) > 0.01]

                    # Calculate totals only from balanced transactions for display
                    balanced_transactions = transaction_balance[abs(transaction_balance['difference']) <= 0.01]
                    balanced_debit = balanced_transactions['חובה'].sum()
                    balanced_credit = balanced_transactions['זכות'].sum()

                    # Add unbalanced transaction totals
                    unbalanced_debit = unbalanced_transactions['חובה'].sum()
                    unbalanced_credit = unbalanced_transactions['זכות'].sum()

                    # For a clean display, show only the actual imbalance from unbalanced transactions
                    actual_imbalance = unbalanced_transactions['difference'].sum() if len(unbalanced_transactions) > 0 else 0.0

                    total_debit = df['חובה'].sum()
                    total_credit = df['זכות'].sum()

                    # Count how many transactions are unbalanced
                    unbalanced_count = len(unbalanced_transactions)

                    print(f"Debug: Sheet '{hebrew_name}' - {unbalanced_count} unbalanced transactions out of {len(transaction_balance)} total")
                    print(f"Debug: Actual imbalance from unbalanced transactions: {actual_imbalance}")
                    if unbalanced_count > 0:
                        print(f"Debug: Individual unbalanced transactions:")
                        for _, row in unbalanced_transactions.iterrows():
                            print(f"  Transaction {row['טרנזקציה']}: Debit={row['חובה']}, Credit={row['זכות']}, Diff={row['difference']}")
                    sys.stdout.flush()

                    # For balance validation: always show total debit/credit from ALL transactions in the sheet
                    # This gives the user the full picture of the sheet totals
                    total_debit_all_transactions = transaction_balance['חובה'].sum()
                    total_credit_all_transactions = transaction_balance['זכות'].sum()

                    # The difference between total debit and total credit for the whole sheet
                    sheet_difference = total_debit_all_transactions - total_credit_all_transactions

                    results[hebrew_name] = {
                        'total_debit': total_debit_all_transactions,
                        'total_credit': total_credit_all_transactions,
                        'difference': sheet_difference,
                        'balanced': abs(sheet_difference) <= 0.01,
                        'unbalanced_transactions': unbalanced_count
                    }
                else:
                    # Fallback to old logic if transaction column missing
                    total_debit = df['חובה'].sum()
                    total_credit = df['זכות'].sum()
                    difference = total_debit - total_credit
                    results[hebrew_name] = {
                        'total_debit': total_debit,
                        'total_credit': total_credit,
                        'difference': difference,
                        'balanced': abs(difference) <= 0.01
                    }

        return results

    def get_problematic_transactions(self):
        """Get transactions where debit != credit for each sheet"""
        problematic_transactions = []

        # Hebrew names mapping
        hebrew_names = {
            'without_ad': 'ללא פרסומים',
            'advertisement': 'פרסומים',
            'rest': 'נתונים נוספים'
        }

        for name, df in [('without_ad', self.without_advertisement),
                        ('advertisement', self.advertisment),
                        ('rest', self.rest)]:
            if df is not None and len(df) > 0:
                hebrew_name = hebrew_names[name]

                # Check if this sheet has unbalanced transactions using same logic as validation
                if 'טרנזקציה' in df.columns and 'חובה' in df.columns and 'זכות' in df.columns:
                    # Group by transaction and check balance for each transaction
                    transaction_balance = df.groupby('טרנזקציה').agg({
                        'חובה': 'sum',
                        'זכות': 'sum'
                    }).reset_index()

                    # Calculate difference for each transaction
                    transaction_balance['difference'] = transaction_balance['חובה'] - transaction_balance['זכות']

                    # Find individual transactions where debit != credit
                    unbalanced_transactions = transaction_balance[abs(transaction_balance['difference']) > 0.01]['טרנזקציה'].tolist()

                    if unbalanced_transactions:  # Sheet has individual unbalanced transactions
                        print(f"Debug: Sheet '{hebrew_name}' - Found {len(unbalanced_transactions)} unbalanced transactions out of {len(transaction_balance)} total transactions")
                        sys.stdout.flush()
                        # Get all rows for unbalanced transactions
                        problematic_df = df[df['טרנזקציה'].isin(unbalanced_transactions)].copy()
                        problematic_df['גיליון'] = hebrew_name

                        # Create transaction URL column
                        problematic_df['קישור טרנזקציה'] = 'https://tickets.hapoel.co.il/Transaction2/Details?id=' + problematic_df['טרנזקציה'].astype(str)

                        # Select relevant columns for the problematic transactions table
                        display_columns = ['מס.סידורי', 'טרנזקציה', 'תאריך העסקה', 'שם המוצר',
                                         'חובה', 'זכות', 'חשבון בחובה', 'חשבון בזכות', 'גיליון', 'קישור טרנזקציה']

                        # Only include columns that exist
                        available_columns = [col for col in display_columns if col in problematic_df.columns]
                        problematic_subset = problematic_df[available_columns]

                        problematic_transactions.append(problematic_subset)
                else:
                    print(f"Debug: Sheet '{hebrew_name}' - Missing required columns for transaction analysis")

        # Combine all problematic transactions into one dataframe
        if problematic_transactions:
            combined_problematic = pd.concat(problematic_transactions, ignore_index=True)
            # Reset sequential numbering
            combined_problematic['מס.סידורי'] = range(1, len(combined_problematic) + 1)
            return combined_problematic
        else:
            return pd.DataFrame()  # Empty dataframe if no problems

# Store session data temporarily (in production, use Redis/DB)
app_sessions = {}

@app.route('/')
def home_page():
    """Main home page with feature overview"""
    return render_template('home.html')

@app.route('/journal')
def journal_page():
    """Journal command page - current upload functionality"""
    return render_template('upload.html')

@app.route('/payment-mapping')
def payment_mapping_page():
    """Payment mapping page - new feature placeholder"""
    return render_template('payment_mapping.html')

@app.route('/csv-filter')
def csv_filter_page():
    """CSV Filter and Table Display page"""
    return render_template('csv_filter.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle CSV file upload and processing"""
    if 'file' not in request.files:
        flash('לא נבחר קובץ', 'error')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('לא נבחר קובץ', 'error')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        try:
            # Create unique filename to avoid conflicts
            unique_id = str(uuid.uuid4())[:8]
            filename = secure_filename(f"{unique_id}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Process the file
            processor = BookkeepingProcessor(file_path)
            results = processor.process()
            validation = processor.get_balance_validation()
            problematic_transactions = processor.get_problematic_transactions()

            # Store results in session-like structure
            session_id = unique_id
            app_sessions[session_id] = {
                'results': results,
                'validation': validation,
                'problematic_transactions': problematic_transactions,
                'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'original_filename': file.filename
            }

            # Clean up uploaded CSV
            try:
                os.remove(file_path)
            except:
                pass

            return redirect(url_for('results_page', session_id=session_id))

        except Exception as e:
            import traceback
            print(f"Error in journal processing: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            flash(f'שגיאה בעיבוד הקובץ: {str(e)}', 'error')
            return redirect(url_for('journal_page'))

    else:
        flash('סוג קובץ לא נתמך. אנא העלה קובץ CSV בלבד.', 'error')
        return redirect(url_for('journal_page'))

@app.route('/results/<session_id>')
def results_page(session_id):
    """Display processing results"""
    if session_id not in app_sessions:
        flash('תוצאות לא נמצאו', 'error')
        return redirect(url_for('journal_page'))

    session_data = app_sessions[session_id]
    filename = session_data['results']['filename']

    return render_template('results.html',
                         session_data=session_data,
                         filename=filename,
                         session_id=session_id)

@app.route('/download/<session_id>')
def download_file(session_id):
    """Download processed Excel file"""
    try:
        if session_id not in app_sessions:
            flash('קובץ לא נמצא', 'error')
            return redirect(url_for('journal_page'))

        session_data = app_sessions[session_id]
        file_path = session_data['results']['output_path']
        filename = session_data['results']['filename']

        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            flash('קובץ לא נמצא', 'error')
            return redirect(url_for('journal_page'))
    except Exception as e:
        flash(f'שגיאה בהורדת הקובץ: {str(e)}', 'error')
        return redirect(url_for('journal_page'))

@app.route('/upload-csv-filter', methods=['POST'])
def upload_csv_filter():
    """Handle CSV file upload for filtering"""
    if 'file' not in request.files:
        return jsonify({'error': 'לא נבחר קובץ'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'לא נבחר קובץ'})

    if file and allowed_file(file.filename):
        try:
            # Create unique filename
            unique_id = str(uuid.uuid4())[:8]
            filename = secure_filename(f"{unique_id}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Load CSV data
            df = pd.read_csv(file_path)

            # Process the data immediately with filters
            session_id = unique_id

            # Apply filters to get initial results
            filtered_df = df.copy()

            # Apply default filters
            if 'Status' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Status'] == 'Active']

            if 'Type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Type'] == 'Sale']

            # Price != 0
            price_cols = [col for col in filtered_df.columns if 'price' in col.lower()]
            if price_cols:
                for col in price_cols:
                    filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') != 0]

            if 'Payment type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Payment type'] == 'PayType_External payment cards']

            # Select display columns
            display_columns = ['Product', 'Id', 'Fan / Company', 'User Id', 'Price', 'Base price', 'Date']
            available_display_cols = [col for col in display_columns if col in filtered_df.columns]

            if available_display_cols:
                display_df = filtered_df[available_display_cols]
            else:
                display_df = filtered_df

            # Format Date column to show only date without time
            if 'Date' in display_df.columns:
                try:
                    display_df = display_df.copy()  # Fix pandas warning
                    display_df['Date'] = pd.to_datetime(display_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
                except AttributeError:
                    # If already string, leave as is
                    pass

            # Create summary table grouped by User Id, Fan/Company, and Product
            summary_data = []
            if len(display_df) > 0:
                # Group by User Id, Fan/Company, and Product
                grouping_cols = ['User Id', 'Fan / Company', 'Product']
                available_grouping_cols = [col for col in grouping_cols if col in display_df.columns]

                if available_grouping_cols:
                    # Build aggregation dict based on available columns
                    agg_dict = {'Id': 'count'}  # Count of rows

                    if 'Price' in display_df.columns:
                        agg_dict['Price'] = 'sum'
                    if 'Base price' in display_df.columns:
                        agg_dict['Base price'] = 'sum'
                    if 'Date' in display_df.columns:
                        agg_dict['Date'] = 'first'

                    summary_groups = display_df.groupby(available_grouping_cols).agg(agg_dict).reset_index()

                    # Rename the count column
                    summary_groups = summary_groups.rename(columns={'Id': 'Amount (Count)'})

                    # Reorder columns
                    summary_columns = available_grouping_cols + ['Amount (Count)', 'Price', 'Base price', 'Date']
                    available_summary_cols = [col for col in summary_columns if col in summary_groups.columns]
                    summary_data = summary_groups[available_summary_cols].to_dict('records')

            # Store processed data in session
            app_sessions[session_id] = {
                'csv_data': df.to_dict('records'),
                'filtered_data': display_df.to_dict('records'),
                'summary_data': summary_data,
                'columns': list(display_df.columns),
                'summary_columns': available_summary_cols if summary_data else [],
                'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'original_filename': file.filename,
                'total_rows': len(display_df),
                'original_rows': len(df),
                'summary_rows': len(summary_data)
            }

            # Clean up uploaded file
            try:
                os.remove(file_path)
            except:
                pass

            return jsonify({
                'success': True,
                'redirect_url': f'/csv-results/{session_id}'
            })

        except Exception as e:
            import traceback
            print(f"Error in CSV processing: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'שגיאה בעיבוד הקובץ: {str(e)}'})
    else:
        return jsonify({'error': 'סוג קובץ לא נתמך. אנא העלה קובץ CSV בלבד.'})

@app.route('/csv-results/<session_id>')
def csv_results_page(session_id):
    """Display CSV filtering results"""
    if session_id not in app_sessions:
        flash('תוצאות לא נמצאו', 'error')
        return redirect(url_for('payment_mapping_page'))

    session_data = app_sessions[session_id]
    return render_template('csv_results.html',
                         session_data=session_data,
                         session_id=session_id)

@app.route('/filter-csv', methods=['POST'])
def filter_csv():
    """Apply filters to CSV data"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filters = data.get('filters', {})

        if session_id not in app_sessions:
            return jsonify({'error': 'נתונים לא נמצאו'})

        df = pd.DataFrame(app_sessions[session_id]['csv_data'])

        # Apply filters
        filtered_df = df.copy()

        # Status = Active
        if 'Status' in filtered_df.columns and filters.get('status_active', True):
            filtered_df = filtered_df[filtered_df['Status'] == 'Active']

        # Type = Sale
        if 'Type' in filtered_df.columns and filters.get('type_sale', True):
            filtered_df = filtered_df[filtered_df['Type'] == 'Sale']

        # Price != 0
        if filters.get('price_not_zero', True):
            price_cols = [col for col in filtered_df.columns if 'price' in col.lower()]
            if price_cols:
                for col in price_cols:
                    filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') != 0]

        # Payment type = PayType_External payment cards
        if 'Payment type' in filtered_df.columns and filters.get('payment_type_external', True):
            filtered_df = filtered_df[filtered_df['Payment type'] == 'PayType_External payment cards']

        # Select specific columns for display
        display_columns = ['Product', 'Id', 'Fan / Company', 'User Id', 'Price', 'Base price', 'Date']
        available_display_cols = [col for col in display_columns if col in filtered_df.columns]

        if available_display_cols:
            display_df = filtered_df[available_display_cols]
        else:
            display_df = filtered_df

        return jsonify({
            'success': True,
            'data': display_df.to_dict('records'),
            'columns': list(display_df.columns),
            'total_rows': len(display_df),
            'original_rows': len(df)
        })

    except Exception as e:
        return jsonify({'error': f'שגיאה בסינון הנתונים: {str(e)}'})

@app.route('/download-filtered-csv/<session_id>')
def download_filtered_csv(session_id):
    """Download filtered CSV data"""
    try:
        data = request.args
        filters = {
            'status_active': data.get('status_active', 'true') == 'true',
            'type_sale': data.get('type_sale', 'true') == 'true',
            'price_not_zero': data.get('price_not_zero', 'true') == 'true',
            'payment_type_external': data.get('payment_type_external', 'true') == 'true'
        }

        if session_id not in app_sessions:
            flash('נתונים לא נמצאו', 'error')
            return redirect(url_for('csv_filter_page'))

        df = pd.DataFrame(app_sessions[session_id]['csv_data'])

        # Apply same filters
        filtered_df = df.copy()

        if 'Status' in filtered_df.columns and filters['status_active']:
            filtered_df = filtered_df[filtered_df['Status'] == 'Active']

        if 'Type' in filtered_df.columns and filters['type_sale']:
            filtered_df = filtered_df[filtered_df['Type'] == 'Sale']

        if filters['price_not_zero']:
            price_cols = [col for col in filtered_df.columns if 'price' in col.lower()]
            if price_cols:
                for col in price_cols:
                    filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') != 0]

        if 'Payment type' in filtered_df.columns and filters['payment_type_external']:
            filtered_df = filtered_df[filtered_df['Payment type'] == 'PayType_External payment cards']

        # Select display columns
        display_columns = ['Product', 'Id', 'Fan / Company', 'User Id', 'Price', 'Base price', 'Date']
        available_display_cols = [col for col in display_columns if col in filtered_df.columns]

        if available_display_cols:
            filtered_df = filtered_df[available_display_cols]

        # Save to temporary file
        output_filename = f"filtered_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        filtered_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    except Exception as e:
        flash(f'שגיאה בהורדת הקובץ: {str(e)}', 'error')
        return redirect(url_for('csv_filter_page'))

@app.route('/download-summary-csv/<session_id>')
def download_summary_csv(session_id):
    """Download summary CSV data"""
    try:
        if session_id not in app_sessions:
            flash('נתונים לא נמצאו', 'error')
            return redirect(url_for('payment_mapping_page'))

        session_data = app_sessions[session_id]
        summary_data = session_data.get('summary_data', [])
        summary_columns = session_data.get('summary_columns', [])

        if not summary_data:
            flash('אין נתונים מסוכמים להורדה', 'error')
            return redirect(url_for('csv_results_page', session_id=session_id))

        # Create DataFrame from summary data
        summary_df = pd.DataFrame(summary_data)

        # Save to temporary file
        output_filename = f"summary_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        summary_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    except Exception as e:
        flash(f'שגיאה בהורדת הקובץ: {str(e)}', 'error')
        return redirect(url_for('csv_results_page', session_id=session_id))

@app.route('/download-problematic-transactions/<session_id>')
def download_problematic_transactions(session_id):
    """Download problematic transactions CSV data"""
    try:
        if session_id not in app_sessions:
            flash('נתונים לא נמצאו', 'error')
            return redirect(url_for('journal_page'))

        session_data = app_sessions[session_id]
        problematic_transactions = session_data.get('problematic_transactions', pd.DataFrame())

        if problematic_transactions.empty:
            flash('אין עסקאות בעייתיות להורדה', 'error')
            return redirect(url_for('results_page', session_id=session_id))

        # Create DataFrame from problematic transactions
        # Save to temporary file
        output_filename = f"problematic_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        problematic_transactions.to_csv(output_path, index=False, encoding='utf-8-sig')

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    except Exception as e:
        flash(f'שגיאה בהורדת הקובץ: {str(e)}', 'error')
        return redirect(url_for('results_page', session_id=session_id))

@app.errorhandler(413)
def too_large(e):
    flash("קובץ גדול מדי. גודל מקסימלי: 16MB", 'error')
    return redirect(url_for('journal_page'))

@app.errorhandler(404)
def not_found(e):
    return render_template('upload.html'), 404

if __name__ == '__main__':
    # Check if running locally or in production
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('RAILWAY_ENVIRONMENT') != 'production'

    if debug:
        print(" הפועל ירושלים כדורסל - מערכת הנהלת חשבונות")
        print(f" האפליקציה רצה על: http://localhost:{port}")
        print(" תיקיית עבודה:", os.getcwd())

    app.run(debug=debug, host='0.0.0.0', port=port)