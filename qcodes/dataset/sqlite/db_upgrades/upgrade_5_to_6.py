import json

from tqdm import tqdm

from qcodes.dataset.dependencies import InterDependencies
from qcodes.dataset.sqlite.connection import ConnectionPlus, atomic
from qcodes.dataset.sqlite.queries import get_run_description, \
    update_run_description
from qcodes.dataset.sqlite.query_helpers import one
from qcodes.dataset.sqlite_base import atomic_transaction


def upgrade_5_to_6(conn: ConnectionPlus) -> None:
    """
    Perform the upgrade from version 5 to version 6.

    The upgrade ensures that the runs_description has a top-level entry
    called 'version'. Note that version changes of the runs_description will
    not be tracked as schema upgrades.
    """
    no_of_runs_query = "SELECT max(run_id) FROM runs"
    no_of_runs = one(atomic_transaction(conn, no_of_runs_query), 'max(run_id)')
    no_of_runs = no_of_runs or 0

    # If one run fails, we want the whole upgrade to roll back, hence the
    # entire upgrade is one atomic transaction

    with atomic(conn) as conn:
        pbar = tqdm(range(1, no_of_runs+1))
        pbar.set_description("Upgrading database, version 5 -> 6")

        empty_idps_ser = InterDependencies().serialize()

        for run_id in pbar:
            json_str = get_run_description(conn, run_id)
            if json_str is None:
                new_json = json.dumps({'version': 0,
                                       'interdependencies': empty_idps_ser})
            else:
                ser = json.loads(json_str)
                new_ser = {'version': 0}  # let 'version' be the first entry
                new_ser['interdependencies'] = ser['interdependencies']
                new_json = json.dumps(new_ser)
            update_run_description(conn, run_id, new_json)
