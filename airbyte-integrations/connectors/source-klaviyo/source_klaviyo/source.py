#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from typing import Any, List, Mapping

from airbyte_cdk.sources.declarative.yaml_declarative_source import YamlDeclarativeSource
from airbyte_cdk.sources.streams import Stream
from source_klaviyo.streams import Campaigns, CampaignsDetailed, Flows
from source_klaviyo.custom_authenticators import KlaviyoOauth2Authenticator

class SourceKlaviyo(YamlDeclarativeSource):
    def __init__(self) -> None:
        super().__init__(**{"path_to_yaml": "manifest.yaml"})

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        Discovery method, returns available streams
        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """
        
        if config['credentials']['auth_type']=='oauth':
            auth = {
                'authenticator': KlaviyoOauth2Authenticator(
                    token_refresh_endpoint="https://a.klaviyo.com/oauth/token",
                    client_id=config['credentials']["client_id"],
                    client_secret=config['credentials']["client_secret"],
                    refresh_token=config['credentials']["refresh_token"],
                )
            }
        else:
            auth = {
                'api_key': config['credentials']['api_key']
            }

        start_date = config.get("start_date")
        streams = super().streams(config)
        streams.extend(
            [
                Campaigns(**auth, start_date=start_date),
                CampaignsDetailed(**auth, start_date=start_date),
                Flows(**auth, start_date=start_date),
            ]
        )
        return streams

    def continue_sync_on_stream_failure(self) -> bool:
        return True
