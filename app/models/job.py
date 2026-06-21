from dataclasses import dataclass


@dataclass
class Job:

    title: str

    company: str

    location: str

    description: str

    apply_link: str

    source: str