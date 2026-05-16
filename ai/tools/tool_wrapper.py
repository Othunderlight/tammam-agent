# from ai.tools.crm_depricated.people import (
#     create_person as _create_person,
# )
# from ai.tools.crm_depricated.people import (
#     delete_person as _delete_person,
# )
# from ai.tools.crm_depricated.people import (
#     get_person as _get_person,
# )
# from ai.tools.crm_depricated.people import (
#     get_person_context as _get_person_context,
# )
# from ai.tools.crm_depricated.people import (
#     import_people as _import_people,
# )

# # People wrappers
# from ai.tools.crm_depricated.people import (
#     list_people as _list_people,
# )
# from ai.tools.crm_depricated.people import (
#     update_person as _update_person,
# )
# Cron wrappers
from ai.tools.cron.tools import (
    create_cron_job as _create_cron_job,
)
from ai.tools.cron.tools import (
    delete_cron_job as _delete_cron_job,
)
from ai.tools.cron.tools import (
    get_cron_job as _get_cron_job,
)
from ai.tools.cron.tools import (
    list_cron_jobs as _list_cron_jobs,
)
from ai.tools.cron.tools import (
    pause_cron_job as _pause_cron_job,
)
from ai.tools.cron.tools import (
    resume_cron_job as _resume_cron_job,
)
from ai.tools.cron.tools import (
    trigger_cron_job as _trigger_cron_job,
)
from ai.tools.cron.tools import (
    update_cron_job as _update_cron_job,
)
from ai.tools.tool_utils import wrap_with_api_key

# list_people = wrap_with_api_key(_list_people)
# get_person = wrap_with_api_key(_get_person)
# get_person_context = wrap_with_api_key(_get_person_context)
# create_person = wrap_with_api_key(_create_person)
# update_person = wrap_with_api_key(_update_person)
# delete_person = wrap_with_api_key(_delete_person)
# import_people = wrap_with_api_key(_import_people)
# # Company wrappers
# from ai.tools.crm_depricated.company import (
#     create_company as _create_company,
# )
# from ai.tools.crm_depricated.company import (
#     delete_company as _delete_company,
# )
# from ai.tools.crm_depricated.company import (
#     get_company as _get_company,
# )
# from ai.tools.crm_depricated.company import (
#     import_companies as _import_companies,
# )
# from ai.tools.crm_depricated.company import (
#     list_companies as _list_companies,
# )
# from ai.tools.crm_depricated.company import (
#     update_company as _update_company,
# )
# list_companies = wrap_with_api_key(_list_companies)
# get_company = wrap_with_api_key(_get_company)
# create_company = wrap_with_api_key(_create_company)
# update_company = wrap_with_api_key(_update_company)
# delete_company = wrap_with_api_key(_delete_company)
# import_companies = wrap_with_api_key(_import_companies)
# # Task wrappers
# from ai.tools.crm_depricated.tasks import (
#     create_task as _create_task,
# )
# from ai.tools.crm_depricated.tasks import (
#     delete_task as _delete_task,
# )
# from ai.tools.crm_depricated.tasks import (
#     get_task as _get_task,
# )
# from ai.tools.crm_depricated.tasks import (
#     import_tasks as _import_tasks,
# )
# from ai.tools.crm_depricated.tasks import (
#     list_tasks as _list_tasks,
# )
# from ai.tools.crm_depricated.tasks import (
#     update_task as _update_task,
# )
# list_tasks = wrap_with_api_key(_list_tasks)
# get_task = wrap_with_api_key(_get_task)
# create_task = wrap_with_api_key(_create_task)
# update_task = wrap_with_api_key(_update_task)
# delete_task = wrap_with_api_key(_delete_task)
# import_tasks = wrap_with_api_key(_import_tasks)
# # Note wrappers
# from ai.tools.crm_depricated.notes import (
#     create_note as _create_note,
# )
# from ai.tools.crm_depricated.notes import (
#     delete_note as _delete_note,
# )
# from ai.tools.crm_depricated.notes import (
#     get_note as _get_note,
# )
# from ai.tools.crm_depricated.notes import (
#     import_notes as _import_notes,
# )
# from ai.tools.crm_depricated.notes import (
#     list_notes as _list_notes,
# )
# from ai.tools.crm_depricated.notes import (
#     update_note as _update_note,
# )
# list_notes = wrap_with_api_key(_list_notes)
# get_note = wrap_with_api_key(_get_note)
# create_note = wrap_with_api_key(_create_note)
# update_note = wrap_with_api_key(_update_note)
# delete_note = wrap_with_api_key(_delete_note)
# import_notes = wrap_with_api_key(_import_notes)
# # Search wrappers
# from ai.tools.crm_depricated.search import (
#     global_search as _global_search,
# )
# global_search = wrap_with_api_key(_global_search)
# User Profile wrappers
from ai.tools.usr.prefrence import (
    manage_user_profile as _manage_user_profile,
)

manage_user_profile = wrap_with_api_key(_manage_user_profile)


list_cron_jobs = wrap_with_api_key(_list_cron_jobs)
get_cron_job = wrap_with_api_key(_get_cron_job)
create_cron_job = wrap_with_api_key(_create_cron_job)
update_cron_job = wrap_with_api_key(_update_cron_job)
delete_cron_job = wrap_with_api_key(_delete_cron_job)
pause_cron_job = wrap_with_api_key(_pause_cron_job)
resume_cron_job = wrap_with_api_key(_resume_cron_job)
trigger_cron_job = wrap_with_api_key(_trigger_cron_job)
