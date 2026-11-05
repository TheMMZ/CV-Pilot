from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Entry(StrictModel):
    title: str = Field(max_length=2000)
    organization: str = Field(max_length=2000)
    dates: str = Field(max_length=2000)
    bullets: list[str] = Field(default_factory=list, max_length=100)

class Project(StrictModel):
    name: str
    status: Literal['planned', 'in progress', 'completed']
    description: str
    skills: list[str] = Field(default_factory=list)

class Profile(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    headline: str
    email: str
    phone: str = ''
    github: str = ''
    summary: str
    skills: list[str] = Field(max_length=100)
    education: list[Entry] = Field(default_factory=list, max_length=20)
    experience: list[Entry] = Field(default_factory=list, max_length=30)
    projects: list[Project] = Field(default_factory=list, max_length=30)
    languages: list[str] = Field(default_factory=list)

class Job(StrictModel):
    title: str = Field(min_length=2, max_length=2000)
    company: str = Field(min_length=1, max_length=2000)
    description: str = Field(min_length=30, max_length=40000)
    url: str = ''

    @field_validator('url')
    @classmethod
    def http_url(cls, value):
        if value and (urlparse(value).scheme not in ('http', 'https') or not urlparse(value).hostname):
            raise ValueError('Use an HTTP(S) application URL.')
        return value
