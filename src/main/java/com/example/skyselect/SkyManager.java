package com.example.skyselect;

import net.minecraft.client.Minecraft;
import net.minecraft.server.packs.repository.Pack;
import net.minecraft.server.packs.repository.PackRepository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Each preset is a built-in resource pack containing OptiFine-format sky files, which Skyboxify
 * reads. "Selecting a sky" = enabling exactly one of those packs and reloading resources.
 * The choice persists because it is stored in options.txt like any other resource pack.
 */
public final class SkyManager {
    private SkyManager() {}

    private static boolean isOurs(String packId) {
        for (SkyPreset p : SkyPreset.values()) {
            if (matches(packId, p)) return true;
        }
        return false;
    }

    private static boolean matches(String packId, SkyPreset p) {
        return packId.contains(SkySelectMod.MOD_ID) && packId.endsWith(p.id);
    }

    public static Optional<SkyPreset> active() {
        PackRepository repo = Minecraft.getInstance().getResourcePackRepository();
        for (String id : repo.getSelectedIds()) {
            for (SkyPreset p : SkyPreset.values()) {
                if (matches(id, p)) return Optional.of(p);
            }
        }
        return Optional.empty();
    }

    /** Enable {@code preset} (and disable every other Sky Select pack). {@code null} = no sky pack. */
    public static void apply(SkyPreset preset) {
        Minecraft mc = Minecraft.getInstance();
        PackRepository repo = mc.getResourcePackRepository();
        repo.reload();

        List<String> selected = new ArrayList<>(repo.getSelectedIds());
        selected.removeIf(SkyManager::isOurs);

        if (preset != null) {
            String found = null;
            for (String id : repo.getAvailableIds()) {
                if (matches(id, preset)) { found = id; break; }
            }
            if (found == null) { // fallback: match by the pack's display title
                for (Pack pack : repo.getAvailablePacks()) {
                    if (pack.getTitle().getString().contains(preset.displayName)) { found = pack.getId(); break; }
                }
            }
            if (found == null) {
                SkySelectMod.LOGGER.error("Sky pack for preset {} not found among {}", preset.id, repo.getAvailableIds());
                return;
            }
            selected.add(found);
        }

        repo.setSelected(selected);
        // Saves options.txt and reloads resources if the selection changed.
        mc.options.updateResourcePacks(repo);
    }
}
