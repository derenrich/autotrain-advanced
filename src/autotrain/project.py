"""
Copyright 2023 The HuggingFace Team
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from loguru import logger

from autotrain.languages import SUPPORTED_LANGUAGES
from autotrain.tasks import TASKS
from autotrain.utils import http_post, user_authentication


@dataclass
class Project:
    token: str
    name: str
    username: str
    task: str
    hub_model: Optional[str] = None
    job_params: Optional[List[Dict]] = None

    def __post_init__(self):
        if self.token is None:
            raise ValueError("❌ Please login using `huggingface-cli login`")

        if self.hub_model is not None and len(self.job_params) == 0:
            raise ValueError("❌ Job parameters are required when hub model is specified.")

        if len(self.job_params) == 1 and self.hub_model is None:
            if "source_language" in self.job_params[0] and "target_language" not in self.job_params[0]:
                self.language = self.job_params[0]["source_language"]
                # remove source language from job params
                self.job_params[0].pop("source_language")
            elif "source_language" in self.job_params[0] and "target_language" in self.job_params[0]:
                self.language = f'{self.job_params[0]["target_language"]}2{self.job_params[0]["source_language"]}'
                # remove source and target language from job params
                self.job_params[0].pop("source_language")
                self.job_params[0].pop("target_language")
            else:
                self.language = "unk"

            if "max_models" in self.job_params[0]:
                self.max_models = self.job_params[0]["max_models"]
                self.job_params[0].pop("max_models")
            elif "max_models" not in self.job_params[0] and "source_language" in self.job_params[0]:
                raise ValueError("❌ Please specify max_models in job_params when using AutoTrain model")
        else:
            self.language = "unk"
            self.max_models = 1

    def create(self):
        """Create a project and return it"""
        task_id = TASKS.get(self.task)
        if task_id is None:
            raise ValueError(f"❌ Invalid task selected. Please choose one of {TASKS.keys()}")
        language = str(self.language).strip().lower()
        if task_id is None:
            raise ValueError(f"❌ Invalid task specified. Please choose one of {list(TASKS.keys())}")

        if self.hub_model is not None:
            language = "unk"

        if language not in SUPPORTED_LANGUAGES:
            raise ValueError("❌ Invalid language. Please check supported languages in AutoTrain documentation.")

        payload = {
            "username": self.username,
            "proj_name": self.name,
            "task": task_id,
            "config": {
                "advanced": True,
                "language": language,
                "max_models": self.max_models,
                "hub_model": self.hub_model,
                "params": self.job_params,
            },
        }
        logger.info(payload)
        json_resp = http_post(path="/projects/create", payload=payload, token=self.token).json()
        proj_name = json_resp["proj_name"]
        created = json_resp["created"]

        if created is True:
            return proj_name
        else:
            raise ValueError(f"❌ Project with name {proj_name} already exists.")