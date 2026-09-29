package com.velo.vpn.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.LockClock
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.VpnKey
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.data.StoreItemDto
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.StoreViewModel
import com.velo.vpn.ui.VeloViewModel
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.HeartPink
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun StoreScreen(nav: NavHostController, vm: StoreViewModel, accountVm: AccountViewModel, veloVm: VeloViewModel) {
    val state by vm.state.collectAsState()
    val account by accountVm.state.collectAsState()
    LaunchedEffect(Unit) { if (account.loggedIn) vm.refresh() }

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).verticalScroll(rememberScrollState()).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            VeloHeader(showBack = true, hearts = state.catalog?.heartBalance ?: account.hearts, onBack = { nav.popBackStack() })
            Text("فروشگاه قلب‌ها", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
            Text("با قلب‌ها قابلیت‌های اضافه Velo را فعال کنید.", color = Muted)

            if (!account.loggedIn) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("قلب‌ها و خریدهای فروشگاه باید روی حساب شما ذخیره شوند.", fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(10.dp))
                    PrimaryButton("ورود با ایمیل") { nav.navigate(Routes.Account) }
                }
                return@Column
            }

            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            state.catalog?.items?.forEach { item -> StoreRow(item, state.buyingSku == item.sku) {
                vm.buy(item.sku) {
                    accountVm.refresh()
                    veloVm.refreshServers()
                }
            } }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            state.info?.let { Text(it, color = VeloPurple) }
        }
    }
}

@Composable
private fun StoreRow(item: StoreItemDto, busy: Boolean, onBuy: () -> Unit) {
    val icon: ImageVector = when (item.kind) {
        "server_access" -> Icons.Default.VpnKey
        "speed_boost" -> Icons.Default.Speed
        "static_ip" -> Icons.Default.LockClock
        else -> Icons.Default.AutoAwesome
    }
    VeloCard(Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = VeloPurple, modifier = Modifier.size(28.dp))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(item.title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    if (item.badge.isNotBlank()) {
                        Spacer(Modifier.width(7.dp))
                        AssistChip(onClick = {}, enabled = false, label = { Text(item.badge, fontSize = 10.sp) })
                    }
                }
                Text(item.description, color = Muted, fontSize = 11.sp)
            }
        }
        Spacer(Modifier.height(11.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Favorite, null, tint = HeartPink, modifier = Modifier.size(16.dp))
            Text(" ${item.hearts}", color = HeartPink, fontWeight = FontWeight.Bold)
            Spacer(Modifier.weight(1f))
            when {
                item.owned -> Text("فعال ✓", color = VeloPurple, fontWeight = FontWeight.Bold)
                !item.enabled -> Text("به‌زودی", color = Muted, fontWeight = FontWeight.Bold)
                busy -> CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                else -> Button(onClick = onBuy, enabled = item.affordable) { Text("فعال‌سازی") }
            }
        }
    }
}
