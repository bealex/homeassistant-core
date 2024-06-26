"""Test the Home Assistant SkyConnect config flow failure cases."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from universal_silabs_flasher.const import ApplicationType

from homeassistant.components import usb
from homeassistant.components.hassio.addon_manager import (
    AddonError,
    AddonInfo,
    AddonState,
)
from homeassistant.components.homeassistant_sky_connect.config_flow import (
    STEP_PICK_FIRMWARE_THREAD,
    STEP_PICK_FIRMWARE_ZIGBEE,
)
from homeassistant.components.homeassistant_sky_connect.const import DOMAIN
from homeassistant.components.homeassistant_sky_connect.util import (
    get_otbr_addon_manager,
    get_zigbee_flasher_addon_manager,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .test_config_flow import USB_DATA_ZBT1, delayed_side_effect

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_cannot_probe_firmware(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when firmware cannot be probed."""

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=None,
    ):
        # Start the flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "usb"}, data=usb_data
        )

        # Probing fails
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "unsupported_firmware"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_zigbee_not_hassio_wrong_firmware(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test when the stick is used with a non-hassio setup but the firmware is bad."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.SPINEL,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=False,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "not_hassio"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_zigbee_flasher_addon_already_running(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon is already running."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.SPINEL,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_flasher_manager = Mock(spec_set=get_zigbee_flasher_addon_manager(hass))
    mock_flasher_manager.addon_name = "Silicon Labs Flasher"
    mock_flasher_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.RUNNING,
        update_available=False,
        version="1.0.0",
    )

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_zigbee_flasher_addon_manager",
            return_value=mock_flasher_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )

        # Cannot get addon info
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_already_running"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_zigbee_flasher_addon_info_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.SPINEL,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_flasher_manager = Mock(spec_set=get_zigbee_flasher_addon_manager(hass))
    mock_flasher_manager.addon_name = "Silicon Labs Flasher"
    mock_flasher_manager.async_get_addon_info.side_effect = AddonError()

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_zigbee_flasher_addon_manager",
            return_value=mock_flasher_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )

        # Cannot get addon info
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_info_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_zigbee_flasher_addon_install_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.SPINEL,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_flasher_manager = Mock(spec_set=get_zigbee_flasher_addon_manager(hass))
    mock_flasher_manager.addon_name = "Silicon Labs Flasher"
    mock_flasher_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_flasher_manager.async_install_addon_waiting = AsyncMock(
        side_effect=AddonError()
    )

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_zigbee_flasher_addon_manager",
            return_value=mock_flasher_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )

        # Cannot install addon
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_install_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_zigbee_flasher_addon_set_config_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon cannot be configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.SPINEL,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_flasher_manager = Mock(spec_set=get_zigbee_flasher_addon_manager(hass))
    mock_flasher_manager.addon_name = "Silicon Labs Flasher"
    mock_flasher_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_flasher_manager.async_install_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_flasher_manager.async_set_addon_options = AsyncMock(side_effect=AddonError())

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_zigbee_flasher_addon_manager",
            return_value=mock_flasher_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_set_config_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_zigbee_flasher_run_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon fails to run."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.SPINEL,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_flasher_manager = Mock(spec_set=get_zigbee_flasher_addon_manager(hass))
    mock_flasher_manager.addon_name = "Silicon Labs Flasher"
    mock_flasher_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_flasher_manager.async_install_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_flasher_manager.async_start_addon_waiting = AsyncMock(side_effect=AddonError())

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_zigbee_flasher_addon_manager",
            return_value=mock_flasher_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_start_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_zigbee_flasher_uninstall_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon uninstall fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.SPINEL,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_flasher_manager = Mock(spec_set=get_zigbee_flasher_addon_manager(hass))
    mock_flasher_manager.addon_name = "Silicon Labs Flasher"
    mock_flasher_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_flasher_manager.async_install_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_flasher_manager.async_start_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_flasher_manager.async_uninstall_addon_waiting = AsyncMock(
        side_effect=AddonError()
    )

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_zigbee_flasher_addon_manager",
            return_value=mock_flasher_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        # Uninstall failure isn't critical
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm_zigbee"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_thread_not_hassio(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test when the stick is used with a non-hassio setup and Thread is selected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.EZSP,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=False,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "not_hassio_thread"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_thread_addon_info_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.EZSP,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_otbr_manager = Mock(spec_set=get_otbr_addon_manager(hass))
    mock_otbr_manager.addon_name = "OpenThread Border Router"
    mock_otbr_manager.async_get_addon_info.side_effect = AddonError()

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_otbr_addon_manager",
            return_value=mock_otbr_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )

        # Cannot get addon info
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_info_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_thread_addon_already_running(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when the Thread addon is already running."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.EZSP,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_otbr_manager = Mock(spec_set=get_otbr_addon_manager(hass))
    mock_otbr_manager.addon_name = "OpenThread Border Router"
    mock_otbr_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.RUNNING,
        update_available=False,
        version="1.0.0",
    )
    mock_otbr_manager.async_install_addon_waiting = AsyncMock(side_effect=AddonError())

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_otbr_addon_manager",
            return_value=mock_otbr_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )

        # Cannot install addon
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "otbr_addon_already_running"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_thread_addon_install_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.EZSP,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_otbr_manager = Mock(spec_set=get_otbr_addon_manager(hass))
    mock_otbr_manager.addon_name = "OpenThread Border Router"
    mock_otbr_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_otbr_manager.async_install_addon_waiting = AsyncMock(side_effect=AddonError())

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_otbr_addon_manager",
            return_value=mock_otbr_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )

        # Cannot install addon
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_install_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_thread_addon_set_config_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon cannot be configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.EZSP,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_otbr_manager = Mock(spec_set=get_otbr_addon_manager(hass))
    mock_otbr_manager.addon_name = "OpenThread Border Router"
    mock_otbr_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_otbr_manager.async_install_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_otbr_manager.async_set_addon_options = AsyncMock(side_effect=AddonError())

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_otbr_addon_manager",
            return_value=mock_otbr_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_set_config_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_thread_flasher_run_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon fails to run."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.EZSP,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_otbr_manager = Mock(spec_set=get_otbr_addon_manager(hass))
    mock_otbr_manager.addon_name = "OpenThread Border Router"
    mock_otbr_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_otbr_manager.async_install_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_otbr_manager.async_start_addon_waiting = AsyncMock(side_effect=AddonError())

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_otbr_addon_manager",
            return_value=mock_otbr_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_start_failed"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_config_flow_thread_flasher_uninstall_fails(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test failure case when flasher addon uninstall fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}, data=usb_data
    )

    with patch(
        "homeassistant.components.homeassistant_sky_connect.config_flow.probe_silabs_firmware_type",
        return_value=ApplicationType.EZSP,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    mock_otbr_manager = Mock(spec_set=get_otbr_addon_manager(hass))
    mock_otbr_manager.addon_name = "OpenThread Border Router"
    mock_otbr_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={},
        state=AddonState.NOT_INSTALLED,
        update_available=False,
        version=None,
    )
    mock_otbr_manager.async_install_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_otbr_manager.async_start_addon_waiting = AsyncMock(
        side_effect=delayed_side_effect()
    )
    mock_otbr_manager.async_uninstall_addon_waiting = AsyncMock(
        side_effect=AddonError()
    )

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_otbr_addon_manager",
            return_value=mock_otbr_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done(wait_background_tasks=True)

        # Uninstall failure isn't critical
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm_otbr"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_options_flow_zigbee_to_thread_zha_configured(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test the options flow migration failure, ZHA using the stick."""
    config_entry = MockConfigEntry(
        domain="homeassistant_sky_connect",
        data={
            "firmware": "ezsp",
            "device": usb_data.device,
            "manufacturer": usb_data.manufacturer,
            "pid": usb_data.pid,
            "description": usb_data.description,
            "product": usb_data.description,
            "serial_number": usb_data.serial_number,
            "vid": usb_data.vid,
        },
        version=1,
        minor_version=2,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)

    # Set up ZHA as well
    zha_config_entry = MockConfigEntry(
        domain="zha",
        data={"device": {"path": usb_data.device}},
    )
    zha_config_entry.add_to_hass(hass)

    # Confirm options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Pick Thread
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "zha_still_using_stick"


@pytest.mark.parametrize(
    ("usb_data", "model"),
    [
        (USB_DATA_ZBT1, "Home Assistant Connect ZBT-1"),
    ],
)
async def test_options_flow_thread_to_zigbee_otbr_configured(
    usb_data: usb.UsbServiceInfo, model: str, hass: HomeAssistant
) -> None:
    """Test the options flow migration failure, OTBR still using the stick."""
    config_entry = MockConfigEntry(
        domain="homeassistant_sky_connect",
        data={
            "firmware": "spinel",
            "device": usb_data.device,
            "manufacturer": usb_data.manufacturer,
            "pid": usb_data.pid,
            "description": usb_data.description,
            "product": usb_data.description,
            "serial_number": usb_data.serial_number,
            "vid": usb_data.vid,
        },
        version=1,
        minor_version=2,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)

    # Confirm options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Pick Zigbee
    mock_otbr_manager = Mock(spec_set=get_otbr_addon_manager(hass))
    mock_otbr_manager.addon_name = "OpenThread Border Router"
    mock_otbr_manager.async_get_addon_info.return_value = AddonInfo(
        available=True,
        hostname=None,
        options={"device": usb_data.device},
        state=AddonState.RUNNING,
        update_available=False,
        version="1.0.0",
    )

    with (
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.get_otbr_addon_manager",
            return_value=mock_otbr_manager,
        ),
        patch(
            "homeassistant.components.homeassistant_sky_connect.config_flow.is_hassio",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "otbr_still_using_stick"
