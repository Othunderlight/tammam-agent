from ai.tools.tool_utils import wrap_with_api_key

# People wrappers
from ai.tools.crm.people import (
    list_people as _list_people,
    get_person as _get_person,
    get_person_context as _get_person_context,
    create_person as _create_person,
    update_person as _update_person,
    delete_person as _delete_person,
    import_people as _import_people,
)

list_people = wrap_with_api_key(_list_people)
get_person = wrap_with_api_key(_get_person)
get_person_context = wrap_with_api_key(_get_person_context)
create_person = wrap_with_api_key(_create_person)
update_person = wrap_with_api_key(_update_person)
delete_person = wrap_with_api_key(_delete_person)
import_people = wrap_with_api_key(_import_people)


# Company wrappers
from ai.tools.crm.company import (
    list_companies as _list_companies,
    get_company as _get_company,
    create_company as _create_company,
    update_company as _update_company,
    delete_company as _delete_company,
    import_companies as _import_companies,
)

list_companies = wrap_with_api_key(_list_companies)
get_company = wrap_with_api_key(_get_company)
create_company = wrap_with_api_key(_create_company)
update_company = wrap_with_api_key(_update_company)
delete_company = wrap_with_api_key(_delete_company)
import_companies = wrap_with_api_key(_import_companies)


# Task wrappers
from ai.tools.crm.tasks import (
    list_tasks as _list_tasks,
    get_task as _get_task,
    create_task as _create_task,
    update_task as _update_task,
    delete_task as _delete_task,
    import_tasks as _import_tasks,
)

list_tasks = wrap_with_api_key(_list_tasks)
get_task = wrap_with_api_key(_get_task)
create_task = wrap_with_api_key(_create_task)
update_task = wrap_with_api_key(_update_task)
delete_task = wrap_with_api_key(_delete_task)
import_tasks = wrap_with_api_key(_import_tasks)


# Note wrappers
from ai.tools.crm.notes import (
    list_notes as _list_notes,
    get_note as _get_note,
    create_note as _create_note,
    update_note as _update_note,
    delete_note as _delete_note,
    import_notes as _import_notes,
)

list_notes = wrap_with_api_key(_list_notes)
get_note = wrap_with_api_key(_get_note)
create_note = wrap_with_api_key(_create_note)
update_note = wrap_with_api_key(_update_note)
delete_note = wrap_with_api_key(_delete_note)
import_notes = wrap_with_api_key(_import_notes)


# Search wrappers
from ai.tools.crm.search import (
    global_search as _global_search,
)

global_search = wrap_with_api_key(_global_search)


# User Profile wrappers
from ai.tools.usr.prefrences import (
    manage_user_profile as _manage_user_profile,
)

manage_user_profile = wrap_with_api_key(_manage_user_profile)
