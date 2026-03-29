def generate_job_links(role):
    role_query = role.replace(" ", "%20")

    return {
        "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={role_query}",
        "Indeed": f"https://in.indeed.com/jobs?q={role_query}",
        "Naukri": f"https://www.naukri.com/{role_query.lower()}-jobs",
        "Foundit": f"https://www.foundit.in/srp/results?query={role_query}",
        "Glassdoor": f"https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={role_query}",
        "Freshersworld": f"https://www.freshersworld.com/jobs/jobsearch/{role_query}-jobs",
        "Internshala": f"https://internshala.com/jobs/{role_query.lower()}-jobs/"
    }
