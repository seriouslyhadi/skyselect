package com.example.skyselect;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public class SkySelectScreen extends Screen {
    private static final int PANEL_W = 236;
    private final Screen parent;

    public SkySelectScreen(Screen parent) {
        super(Component.literal("Sky Select"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        int x = 12 + 8;
        int y = 34;
        SkyPreset active = SkyManager.active().orElse(null);

        for (SkyPreset p : SkyPreset.values()) {
            boolean on = p == active;
            Component label = Component.literal((on ? "\u00a7a\u25b6 " : "   ") + p.displayName);
            addRenderableWidget(Button.builder(label, b -> {
                SkyManager.apply(p);
                rebuildWidgets();
            }).bounds(x, y, PANEL_W - 16, 20).build());
            y += 23;
        }

        addRenderableWidget(Button.builder(Component.literal(active == null ? "\u00a7a\u25b6 No Sky Select sky" : "   No Sky Select sky"), b -> {
            SkyManager.apply(null);
            rebuildWidgets();
        }).bounds(x, y, PANEL_W - 16, 20).build());
        y += 28;

        addRenderableWidget(Button.builder(Component.literal("Done"), b -> onClose())
                .bounds(x, y, PANEL_W - 16, 20).build());
    }

    /** Keep the sky visible behind the menu so changes can be previewed live. */
    @Override
    public void renderBackground(GuiGraphics g, int mouseX, int mouseY, float partialTick) {
        if (minecraft != null && minecraft.level == null) {
            super.renderBackground(g, mouseX, mouseY, partialTick);
        }
        g.fill(12, 12, 12 + PANEL_W, this.height - 12, 0xA0000000);
    }

    @Override
    public void render(GuiGraphics g, int mouseX, int mouseY, float partialTick) {
        super.render(g, mouseX, mouseY, partialTick); // calls our renderBackground, then the buttons
        g.drawString(this.font, this.title, 20, 20, 0xFFFFFFFF);

        int ty = this.height - 64;
        SkyPreset active = SkyManager.active().orElse(null);
        if (active != null) {
            g.drawString(this.font, active.description, 20, ty, 0xFFB0B0B0);
        }
        g.drawString(this.font, "Skies show day and night (clear weather).", 20, ty + 14, 0xFF808080);
        g.drawString(this.font, "Requires the Skyboxify mod.", 20, ty + 26, 0xFF808080);
    }

    @Override
    public void onClose() {
        if (minecraft != null) minecraft.setScreen(parent);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
