from app.graph.workflow import (
    workflow
)


def main():

    state = {

        "resume_text": "",

        "jobs": [],

        "matched_jobs": []
    }
    print("USING UPDATED WORKFLOW")

    result = workflow.invoke(
        state
    )

    print("\n")

    print(
        "=" * 50
    )

    print(
        "MATCHED JOBS"
    )

    print(
        "=" * 50
    )

    for job in result[
        "matched_jobs"
    ]:

        print(
            f"""
Title   : {job['title']}
Company : {job['company']}
Score   : {job['score']}
"""
        )


if __name__ == "__main__":

    main()