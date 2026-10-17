#ifdef BZ_TESTS
#include "test.h"
#include "../g_local.h"

void setup_test_world(void);
bool run_test_jass(cstring_t src);
extern player_t *currentplayer;

static gameClient_t *rotate_test_setup(void) {
    gameClient_t *client;
    setup_test_world();
    client = game.clients;
    client->camera.state = (camerasetup_t){
        .position = { 300, 180 }, .viewangles = { 326, 0, 0 },
        .target_distance = 900, .fov = 50, .near_z = 16, .far_z = 5000,
    };
    client->camera.old_state = client->camera.state;
    client->camera.start_time = client->camera.end_time = level.time = 100;
    currentplayer = &client->ps;
    level.started = true;
    level.scriptsStarted = true;
    return client;
}

static void rotate_test_frame(uint32_t now) { level.time = now; G_RunFrame(); }

TEST(wc3_api, camera_rotate_mode_keeps_full_sweep_through_scheduler) {
    gameClient_t *client = rotate_test_setup();
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, 12.566370614, 4.0)\n"
        "endfunction\n"));
    rotate_test_frame(600);
    T_FEQ(client->ps.vieworigin.x, 200, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 280, 0.01f);
    T_FEQ(client->ps.viewangles.z, -90, 0.01f);
    T_FEQ(client->ps.distance, 900, 0.01f);
    rotate_test_frame(1100);
    T_FEQ(client->ps.vieworigin.x, 100, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 180, 0.01f);
    T_FEQ(client->ps.viewangles.z, -180, 0.01f);
    rotate_test_frame(2100);
    T_FEQ(client->ps.vieworigin.x, 300, 0.01f);
    T_FEQ(client->ps.viewangles.z, -360, 0.01f);
    rotate_test_frame(4100);
    T_FEQ(client->ps.vieworigin.x, 300, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 180, 0.01f);
    T_FEQ(client->ps.viewangles.z, -720, 0.01f);
    rotate_test_frame(5100);
    T_FEQ(client->ps.viewangles.z, -720, 0.01f);
    currentplayer = NULL;
}

TEST(wc3_api, camera_rotate_mode_stop_replace_and_immediate_sweep) {
    gameClient_t *client = rotate_test_setup();
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, -3.141592654, 2.0)\n"
        "endfunction\n"));
    level.time = 600;
    T_ASSERT(run_test_jass("function main takes nothing returns nothing\ncall StopCamera()\nendfunction\n"));
    rotate_test_frame(1600);
    T_FEQ(client->ps.vieworigin.x, 270.71068f, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 109.28932f, 0.01f);
    T_FEQ(client->ps.viewangles.z, 45, 0.01f);
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, 1.570796327, 0.0)\n"
        "endfunction\n"));
    rotate_test_frame(1700);
    T_FEQ(client->ps.vieworigin.x, 270.71068f, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 250.71068f, 0.01f);
    T_FEQ(client->ps.viewangles.z, -45, 0.01f);
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, 6.283185307, 4.0)\n"
        "endfunction\n"));
    level.time = 2200;
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call PanCameraToTimed(50.0, 70.0, 1.0)\n"
        "endfunction\n"));
    rotate_test_frame(3200);
    T_FEQ(client->ps.vieworigin.x, 50, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 70, 0.01f);
    T_FEQ(client->ps.viewangles.z, -90, 0.01f);
    currentplayer = NULL;
}

TEST(wc3_save, camera_rotate_mode_continues_after_round_trip) {
    PATHSTR filename;
    gameClient_t *client = rotate_test_setup();
    strlcpy(filename, Test_TempPath("wc3-camera-rotate-save.bin"), sizeof(filename));
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, 12.566370614, 4.0)\n"
        "endfunction\n"));
    rotate_test_frame(600);
    T_ASSERT(WriteGame(filename));
    rotate_test_frame(4100);
    T_ASSERT(ReadGame(filename));
    rotate_test_frame(1100);
    T_FEQ(client->ps.vieworigin.x, 100, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 180, 0.01f);
    T_FEQ(client->ps.viewangles.z, -180, 0.01f);
    rotate_test_frame(4100);
    T_FEQ(client->ps.viewangles.z, -720, 0.01f);
    remove(filename);
    currentplayer = NULL;
}

TEST(wc3_api, camera_rotate_mode_replacement_and_player_input_cancel_motion) {
    gameClient_t *client = rotate_test_setup();
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, 6.283185307, 4.0)\n"
        "endfunction\n"));
    level.time = 1100;
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, -3.141592654, 2.0)\n"
        "endfunction\n"));
    rotate_test_frame(1600);
    T_FEQ(client->ps.vieworigin.x, 270.71068f, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 250.71068f, 0.01f);
    T_FEQ(client->ps.viewangles.z, -45, 0.01f);
    level.time = 2100;
    G_ClientInput(G_GetPlayerEntityByNumber(0), &(inputCmd_t){
        .action = BZ_INPUT_FOCUS, .focus = { 55, 75 } });
    rotate_test_frame(3100);
    T_FEQ(client->ps.vieworigin.x, 55, 0.01f);
    T_FEQ(client->ps.vieworigin.y, 75, 0.01f);
    T_FEQ(client->ps.viewangles.z, 0, 0.01f);

    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraRotateMode(200.0, 180.0, 6.283185307, 4.0)\n"
        "endfunction\n"));
    level.time = 4100;
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  call SetCameraField(CAMERA_FIELD_ROTATION, 120.0, 0.0)\n"
        "endfunction\n"));
    rotate_test_frame(5100);
    T_FEQ(client->ps.viewangles.z, 150, 0.01f);
    T_ASSERT(!client->camera.rotate_active);
    currentplayer = NULL;
}
#endif
