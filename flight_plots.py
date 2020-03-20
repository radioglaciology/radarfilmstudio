from bokeh.io import output_file, show, output_notebook
from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import OpenURL, TapTool

import pandas as pd




pd.read_sql(session.query(Complaint).filter(Complaint.id == 2).statement,session.bind)