import algokit_utils.logic_error
import algosdk
import pytest
from algokit_utils import (
    Account,
    ApplicationClient,
    ApplicationSpecification,
    TransactionParameters,
    get_localnet_default_account,
    get_or_create_kmd_wallet_account, OnCompleteCallParameters,
)
from algosdk import transaction
from algosdk.atomic_transaction_composer import AtomicTransactionComposer
from algosdk.v2client.algod import AlgodClient

from smart_contracts.dao import contract as dao_contract


@pytest.fixture(scope="session")
def dao_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return dao_contract.app.build(algod_client)


@pytest.fixture(scope="session")
def creator_account(algod_client: AlgodClient) -> Account:
    return get_localnet_default_account(algod_client)


@pytest.fixture(scope="session")
def dao_client(
    algod_client: AlgodClient,
    dao_app_spec: ApplicationSpecification,
    creator_account: Account,
) -> ApplicationClient:
    client = ApplicationClient(
        algod_client,
        app_spec=dao_app_spec,
        signer=creator_account,
        template_values={"UPDATABLE": 1, "DELETABLE": 1},
    )
    return client


@pytest.fixture(scope="session")
def other_account(algod_client: AlgodClient) -> Account:
    return get_or_create_kmd_wallet_account(
        algod_client, "tealscript-dao-other", 1_000_000_000
    )


PROPOSAL = "This is another proposal."
END_VOTING = 16927981910


def test_deploy(dao_client: ApplicationClient):
    dao_client.create(proposal=PROPOSAL, end_voting=END_VOTING)


def test_get_proposal(dao_client: ApplicationClient):
    proposal = dao_client.call(dao_contract.get_proposal).return_value
    assert proposal == PROPOSAL
    assert dao_client.get_global_state()["proposal"] == PROPOSAL


def test_get_registered_asa_negative(dao_client: ApplicationClient):
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(dao_contract.get_registered_asa)


def test_bootstrap_negative(
    dao_client: ApplicationClient, creator_account: Account, other_account: Account
):
    # Fund the contract.
    dao_client.algod_client.send_transactions(
        creator_account.signer.sign_transactions(
            [
                algosdk.transaction.PaymentTxn(
                    creator_account.address,
                    dao_client.algod_client.suggested_params(),
                    dao_client.app_address,
                    200_000,
                )
            ],
            [0],
        )
    )

    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(
            dao_contract.bootstrap,
            transaction_parameters=TransactionParameters(
                sender=other_account.address,
                signer=other_account.signer,
                suggested_params=sp,
            ),
        )


def test_bootstrap(dao_client: ApplicationClient):
    # Bootstrap the contract.
    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    dao_client.call(
        dao_contract.bootstrap,
        transaction_parameters=TransactionParameters(suggested_params=sp),
    )


@pytest.fixture(scope="session")
def registered_asa_id(dao_client: ApplicationClient) -> int:
    return dao_client.call(dao_contract.get_registered_asa).return_value


def test_get_registered_id(dao_client: ApplicationClient, registered_asa_id: int):
    assert registered_asa_id == dao_client.get_global_state()["registered_asa_id"]


def test_vote_negative(
    dao_client: ApplicationClient, other_account: Account, registered_asa_id: int
):
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(
            dao_contract.vote,
            in_favor=True,
            registered_asa=registered_asa_id,
            transaction_parameters=TransactionParameters(
                sender=other_account.address,
                signer=other_account.signer,
            ),
        )


def test_register(
    dao_client: ApplicationClient, other_account: Account, registered_asa_id: int
):
    # Opt-in to the Registered ASA.
    dao_client.algod_client.send_transactions(
        other_account.signer.sign_transactions(
            [
                algosdk.transaction.AssetTransferTxn(
                    other_account.address,
                    dao_client.algod_client.suggested_params(),
                    other_account.address,
                    0,
                    registered_asa_id,
                )
            ],
            [0],
        )
    )

    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    dao_client.opt_in(
        dao_contract.register,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
            suggested_params=sp,
        ),
    )

    with pytest.raises(algosdk.error.AlgodHTTPError):
        dao_client.algod_client.send_transactions(
            other_account.signer.sign_transactions(
                [
                    algosdk.transaction.AssetTransferTxn(
                        other_account.address,
                        dao_client.algod_client.suggested_params(),
                        other_account.address,
                        1,
                        registered_asa_id,
                    )
                ],
                [0],
            )
        )


def test_get_votes_negative(dao_client: ApplicationClient):
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(dao_contract.get_votes)


def test_vote_and_get_votes(
    dao_client: ApplicationClient, other_account: Account, registered_asa_id: int
):
    atc = AtomicTransactionComposer()
    dao_client.compose_call(
        atc,
        dao_contract.vote,
        OnCompleteCallParameters(
            sender=other_account.address, signer=other_account.signer
        ),
        in_favor=True,
        registered_asa=registered_asa_id,
    )
    txns = atc.gather_signatures()
    dryrun_request = transaction.create_dryrun(dao_client.algod_client, txns, latest_timestamp=END_VOTING)
    dryrun_response = dao_client.algod_client.dryrun(dryrun_request)
    assert dryrun_response['txns'][0]['app-call-messages'][1] == 'REJECT'

    dao_client.call(
        dao_contract.vote,
        in_favor=True,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
        ),
    )
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 1
    assert votes[1] == 1

    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(
            dao_contract.vote,
            in_favor=False,
            registered_asa=registered_asa_id,
            transaction_parameters=TransactionParameters(
                sender=other_account.address,
                signer=other_account.signer,
            ),
        )
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 1
    assert votes[1] == 1


def test_deregister(
    dao_client: ApplicationClient,
    creator_account: Account,
    other_account: Account,
    registered_asa_id: int,
):
    # This demonstrates that the user is able to close out of the contract.
    sp = dao_client.algod_client.suggested_params()
    sp.fee = 2_000
    sp.flat_fee = True
    dao_client.close_out(
        dao_contract.deregister,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
            suggested_params=sp,
        ),
    )
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 0
    assert votes[1] == 0

    # They are still opted in to the registered ASA with a 0 balance.
    # Therefore, they are free to opt out of the registered ASA.
    user_assets = dao_client.algod_client.account_info(other_account.address)["assets"]
    assert (
        filter(
            lambda asset: asset["asset-id"] == registered_asa_id, user_assets
        ).__next__()["amount"]
        == 0
    )

    # Opt out of the Registered ASA.
    dao_client.algod_client.send_transactions(
        other_account.signer.sign_transactions(
            [
                algosdk.transaction.AssetTransferTxn(
                    other_account.address,
                    dao_client.algod_client.suggested_params(),
                    creator_account.address,
                    0,
                    registered_asa_id,
                    close_assets_to=creator_account.address,
                )
            ],
            [0],
        )
    )
    user_assets = dao_client.algod_client.account_info(other_account.address)["assets"]
    filtered_assets = filter(
        lambda asset: asset["asset-id"] == registered_asa_id, user_assets
    )
    with pytest.raises(StopIteration):
        filtered_assets.__next__()

    # We already demonstrated that the user cannot vote if they are not registered.

    # They can register again (must opt in again to registered ASA).
    dao_client.algod_client.send_transactions(
        other_account.signer.sign_transactions(
            [
                algosdk.transaction.AssetTransferTxn(
                    other_account.address,
                    dao_client.algod_client.suggested_params(),
                    other_account.address,
                    0,
                    registered_asa_id,
                )
            ],
            [0],
        )
    )

    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    dao_client.opt_in(
        dao_contract.register,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
            suggested_params=sp,
        ),
    )

    # They can vote again.
    dao_client.call(
        dao_contract.vote,
        in_favor=False,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address, signer=other_account.signer
        ),
    )
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 1
    assert votes[1] == 0


def test_clear_state(
    dao_client: ApplicationClient, other_account: Account, registered_asa_id: int
):
    dao_client.clear_state(
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
        )
    )

    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 0
    assert votes[1] == 0

    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(
            dao_contract.vote,
            in_favor=True,
            registered_asa=registered_asa_id,
            transaction_parameters=TransactionParameters(
                sender=other_account.address,
                signer=other_account.signer,
            ),
        )

    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.opt_in(
            dao_contract.register,
            registered_asa=registered_asa_id,
            transaction_parameters=TransactionParameters(
                sender=other_account.address,
                signer=other_account.signer,
                suggested_params=sp,
            ),
        )
