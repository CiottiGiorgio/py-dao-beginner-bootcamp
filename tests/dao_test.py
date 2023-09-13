import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient

from smart_contracts.dao import contract as dao_contract


@pytest.fixture(scope="session")
def dao_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return dao_contract.app.build(algod_client)


@pytest.fixture(scope="session")
def dao_client(
    algod_client: AlgodClient, dao_app_spec: ApplicationSpecification
) -> ApplicationClient:
    client = ApplicationClient(
        algod_client,
        app_spec=dao_app_spec,
        signer=get_localnet_default_account(algod_client),
        template_values={"UPDATABLE": 1, "DELETABLE": 1},
    )
    return client


PROPOSAL = "This is another proposal."


def test_deploy(dao_client: ApplicationClient):
    dao_client.create(proposal=PROPOSAL)


def test_get_proposal(dao_client: ApplicationClient):
    proposal = dao_client.call(dao_contract.get_proposal).return_value
    assert proposal == PROPOSAL
    assert dao_client.get_global_state()["proposal"] == PROPOSAL
