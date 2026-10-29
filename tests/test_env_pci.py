from betterbench.env import pci_gpus


def _card(root, name, addr, vendor, resource, link=("16.0 GT/s PCIe", "16")):
    dev = root / "devices" / addr
    dev.mkdir(parents=True)
    (dev / "vendor").write_text(vendor + "\n")
    (dev / "device").write_text("0xe223\n")
    (dev / "resource").write_text(resource)
    (dev / "current_link_speed").write_text(link[0] + "\n")
    (dev / "current_link_width").write_text(link[1] + "\n")
    card = root / "drm" / name
    card.mkdir(parents=True)
    (card / "device").symlink_to(dev)


def test_intel_rebar_on(tmp_path):
    # BAR0 16 MiB registers, BAR2 32 GiB VRAM aperture: Resizable BAR on
    _card(tmp_path, "card0", "0000:03:00.0", "0x8086",
          "0x0000007800000000 0x0000007800ffffff 0x0\n"
          "0x0000000000000000 0x0000000000000000 0x0\n"
          "0x0000007000000000 0x00000077ffffffff 0x0\n")
    (g,) = pci_gpus(str(tmp_path / "drm"))
    assert g["vendor"] == "intel" and g["pci_address"] == "0000:03:00.0"
    assert g["largest_bar_mib"] == 32768 and g["resizable_bar"] == "likely on"
    assert g["current_link_speed"] == "16.0 GT/s PCIe" and g["current_link_width"] == "16"


def test_rebar_off_256mib(tmp_path):
    _card(tmp_path, "card0", "0000:01:00.0", "0x1002",
          "0x00000000e0000000 0x00000000efffffff 0x0\n")
    (g,) = pci_gpus(str(tmp_path / "drm"))
    assert g["vendor"] == "amd" and g["largest_bar_mib"] == 256 and g["resizable_bar"] == "likely off"


def test_skips_non_gpu_vendor_and_duplicate_nodes(tmp_path):
    _card(tmp_path, "card0", "0000:03:00.0", "0x8086", "0x0 0xfffffff 0x0\n")
    (tmp_path / "drm" / "card0-DP-1").mkdir()  # connector node, no device link
    (tmp_path / "drm" / "card1").mkdir()
    (tmp_path / "drm" / "card1" / "device").symlink_to(tmp_path / "devices" / "0000:03:00.0")  # same GPU again
    _card(tmp_path, "card2", "0000:00:02.0", "0x1234", "0x0 0xfff 0x0\n")
    gpus = pci_gpus(str(tmp_path / "drm"))
    assert [g["pci_address"] for g in gpus] == ["0000:03:00.0"]


def test_missing_sysfs_is_empty(tmp_path):
    assert pci_gpus(str(tmp_path / "nope")) == []
