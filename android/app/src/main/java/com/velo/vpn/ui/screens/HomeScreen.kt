package com.velo.vpn.ui.screens

import android.app.Activity
import android.app.Activity.RESULT_OK
import android.net.VpnService
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.VeloViewModel
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloBottomBar
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.Lilac
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun HomeScreen(nav: NavHostController, vm: VeloViewModel, accountVm: AccountViewModel) {
    val state by vm.home.collectAsState()
    val account by accountVm.state.collectAsState()
    val context = LocalContext.current
    val activity = context as? Activity
    val snackbar = remember { SnackbarHostState() }

    val vpnPermission = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == RESULT_OK) vm.connect()
    }

    LaunchedEffect(state.error, state.info) {
        val message = state.error ?: state.info
        if (!message.isNullOrBlank()) {
            snackbar.showSnackbar(message)
            vm.clearNotice()
        }
    }

    LaunchedEffect(account.loggedIn, account.subscriptionActive) {
        if (account.loggedIn) {
            vm.refreshServers()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = { VeloBottomBar(nav, Routes.Home) },
    ) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            VeloHeader()
            Spacer(Modifier.height(8.dp))

            when {
                account.loading -> {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                }

                !account.loggedIn -> {
                    Spacer(Modifier.height(36.dp))
                    Text("اتصال ساده و امن", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
                    Text("برای استفاده از Velo با ایمیل خود وارد شوید.", color = Muted, fontSize = 14.sp)
                    Spacer(Modifier.height(14.dp))
                    PrimaryButton("ورود با ایمیل") { nav.navigate(Routes.Account) }
                }

                !account.subscriptionActive -> {
                    Spacer(Modifier.height(28.dp))
                    VeloCard(Modifier.fillMaxWidth()) {
                        Icon(Icons.Default.WorkspacePremium, null, tint = VeloPurple, modifier = Modifier.size(42.dp))
                        Spacer(Modifier.height(12.dp))
                        Text("اشتراک فعال ندارید", fontSize = 23.sp, fontWeight = FontWeight.ExtraBold)
                        Text("پس از خرید و تأیید ادمین، اشتراک روی همین ایمیل فعال می‌شود.", color = Muted, fontSize = 13.sp)
                        Spacer(Modifier.height(16.dp))
                        PrimaryButton("خرید اشتراک") { nav.navigate(Routes.Premium) }
                    }
                }

                else -> {
                    Spacer(Modifier.height(8.dp))
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        Box(
                            Modifier.size(205.dp).background(Lilac.copy(alpha = .45f), CircleShape),
                            contentAlignment = Alignment.Center,
                        ) {
                            Box(
                                Modifier.size(164.dp).background(MaterialTheme.colorScheme.surface, CircleShape),
                                contentAlignment = Alignment.Center,
                            ) {
                                IconButton(
                                    enabled = !state.busy && state.ready,
                                    onClick = {
                                        if (state.connected) {
                                            vm.disconnect()
                                        } else {
                                            val prepare = VpnService.prepare(context)
                                            if (prepare != null) vpnPermission.launch(prepare) else vm.connect()
                                        }
                                    },
                                    modifier = Modifier
                                        .size(116.dp)
                                        .background(if (state.connected) VeloPurple else Color.Transparent, CircleShape),
                                ) {
                                    if (state.busy) {
                                        CircularProgressIndicator(modifier = Modifier.size(40.dp), color = VeloPurple)
                                    } else {
                                        Icon(
                                            Icons.Default.PowerSettingsNew,
                                            null,
                                            tint = if (state.connected) Color.White else VeloPurple,
                                            modifier = Modifier.size(58.dp),
                                        )
                                    }
                                }
                            }
                        }
                    }

                    Text(
                        if (state.connected) "متصل" else "اتصال",
                        Modifier.align(Alignment.CenterHorizontally),
                        fontSize = 25.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        if (state.connected) state.serverName else "بهترین سرور به‌صورت خودکار انتخاب می‌شود",
                        Modifier.align(Alignment.CenterHorizontally),
                        color = Muted,
                        fontSize = 13.sp,
                    )

                    VeloCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Schedule, null, tint = VeloPurple)
                            Spacer(Modifier.width(10.dp))
                            Column(Modifier.weight(1f)) {
                                Text("اشتراک Premium", fontWeight = FontWeight.Bold)
                                Text(
                                    account.subscriptionEndsAt?.take(10)?.let { "فعال تا $it" } ?: "فعال",
                                    color = Muted,
                                    fontSize = 12.sp,
                                )
                            }
                        }
                    }

                    if (state.takeoverRequired) {
                        VeloCard(Modifier.fillMaxWidth()) {
                            Text("اشتراک روی دستگاه دیگری در حال استفاده است.", fontWeight = FontWeight.Bold)
                            Text("Velo فقط یک اتصال هم‌زمان برای هر حساب اجازه می‌دهد.", color = Muted, fontSize = 12.sp)
                            Spacer(Modifier.height(10.dp))
                            PrimaryButton("قطع دستگاه دیگر و اتصال این دستگاه") {
                                vm.clearNotice()
                                vm.connect(forceTakeover = true)
                            }
                        }
                    }
                }
            }
        }
    }
}
