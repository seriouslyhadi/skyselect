package com.example.skyselect;

import com.mojang.blaze3d.platform.InputConstants;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandManager;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.resource.ResourceManagerHelper;
import net.fabricmc.fabric.api.resource.ResourcePackActivationType;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier; // 1.21.11 name. On older mappings this is ResourceLocation.
import org.lwjgl.glfw.GLFW;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class SkySelectMod implements ClientModInitializer {
    public static final String MOD_ID = "skyselect";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static KeyMapping openKey;

    @Override
    public void onInitializeClient() {
        // 1) Register every preset as an optional built-in resource pack (disabled by default).
        FabricLoader.getInstance().getModContainer(MOD_ID).ifPresent(container -> {
            for (SkyPreset p : SkyPreset.values()) {
                boolean ok = ResourceManagerHelper.registerBuiltinResourcePack(
                        Identifier.fromNamespaceAndPath(MOD_ID, p.id),
                        container,
                        Component.literal("Sky Select: " + p.displayName),
                        ResourcePackActivationType.NORMAL);
                if (!ok) LOGGER.warn("Could not register built-in pack {}", p.id);
            }
        });

        // 2) Key bind (J) to open the GUI.
        KeyMapping.Category category = KeyMapping.Category.register(Identifier.fromNamespaceAndPath(MOD_ID, "main"));
        openKey = KeyBindingHelper.registerKeyBinding(
                new KeyMapping("key.skyselect.open", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_J, category));
        ClientTickEvents.END_CLIENT_TICK.register(mc -> {
            while (openKey.consumeClick()) {
                if (mc.screen == null) mc.setScreen(new SkySelectScreen(null));
            }
        });

        // 3) /skyselect also opens it.
        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) ->
                dispatcher.register(ClientCommandManager.literal("skyselect").executes(ctx -> {
                    Minecraft mc = Minecraft.getInstance();
                    mc.schedule(() -> mc.setScreen(new SkySelectScreen(null)));
                    return 1;
                })));
    }
}
