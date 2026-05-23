from flask import Blueprint, render_template
from utils import login_required

civic_units_bp = Blueprint('civic_units', __name__)


@civic_units_bp.route('/civic-units')
@login_required
def civic_units():
    return render_template('civic_units.html')
