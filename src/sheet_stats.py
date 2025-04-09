import logging
import gspread
from gspread.exceptions import APIError

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STATS_WRITE_RANGE = "G2:H5"
STATS_READ_RANGE = "H3:H5" # Range to read Total, Limit, Left values
STATS_DATA = [
    ["Stats", ""],
    ["Total", "=SUM(C2:C)"],
    ["Limit", 1800],  # Hardcoded limit for now
    ["Left", "=H4-H3"]
]

def update_monthly_stats(worksheet: gspread.Worksheet) -> dict | None:
    """
    Updates the statistics block (Total, Limit, Left) in the given worksheet
    and reads the calculated values back.

    Args:
        worksheet: The gspread Worksheet object to update.
    
    Returns:
        A dictionary containing the stats {'total': ..., 'limit': ..., 'left': ...}
        or None if an error occurred.
    """
    try:
        # Write the stats headers and formulas
        worksheet.update(
            STATS_WRITE_RANGE,
            STATS_DATA,
            value_input_option='USER_ENTERED' # Important for formulas
        )
        logger.info(f"Successfully updated stats structure in worksheet '{worksheet.title}'.")

        # Read the calculated values back
        # Use value_render_option='FORMATTED_VALUE' to get numbers as seen in sheet
        stats_values = worksheet.get(STATS_READ_RANGE, value_render_option='FORMATTED_VALUE')
        
        if len(stats_values) == 3: # Should be [[Total], [Limit], [Left]]
            stats_dict = {
                'total': stats_values[0][0] if stats_values[0] else 'N/A',
                'limit': stats_values[1][0] if stats_values[1] else 'N/A',
                'left': stats_values[2][0] if stats_values[2] else 'N/A'
            }
            logger.info(f"Successfully read stats values: {stats_dict}")
            return stats_dict
        else:
            logger.error(f"Read unexpected number of rows for stats: {len(stats_values)}")
            return None

    except APIError as e:
        logger.error(f"API error during stats update/read in worksheet '{worksheet.title}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during stats update/read in worksheet '{worksheet.title}': {e}")
        return None 