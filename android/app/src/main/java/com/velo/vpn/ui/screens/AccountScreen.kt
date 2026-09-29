package com.velo.vpn.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.HeartPink
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun AccountScreen(nav: NavHostController, vm: AccountViewModel) {
    val state by vm.state.collectAsState()
    var email by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            VeloHeader(showBack = true, hearts = state.hearts, onBack = { nav.popBackStack() })
            Text("حساب کاربری", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)

            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())

            if (state.loggedIn) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("ایمیل", color = Muted, fontSize = 12.sp)
                    Text(state.email, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                    Spacer(Modifier.height(14.dp))
                    Row(Modifier.fillMaxWidth()) {
                        Column(Modifier.weight(1f)) {
                            Icon(Icons.Default.Favorite, null, tint = HeartPink)
                            Text("${state.hearts} قلب", fontWeight = FontWeight.Bold)
                        }
                        Column(Modifier.weight(1f)) {
                            Icon(Icons.Default.WorkspacePremium, null, tint = VeloPurple)
                            Text(if (state.subscriptionActive) "Premium فعال" else "پلن رایگان", fontWeight = FontWeight.Bold)
                            if (state.subscriptionEndsAt != null) Text(state.subscriptionEndsAt.take(10), color = Muted, fontSize = 11.sp)
                        }
                    }
                }
                OutlinedButton(onClick = { vm.logout() }, modifier = Modifier.fillMaxWidth()) { Text("خروج از حساب") }
            } else if (!state.otpSent) {
                Text("فقط زمانی که می‌خواهید خرید، قلب‌ها یا دعوت‌ها محفوظ بمانند به حساب نیاز دارید.", color = Muted)
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("ایمیل") },
                    leadingIcon = { Icon(Icons.Default.Email, null) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    singleLine = true,
                )
                PrimaryButton("ارسال کد ورود") { vm.requestOtp(email) }
            } else {
                Text("کد ۶ رقمی ارسال‌شده به ${state.pendingEmail} را وارد کنید.", color = Muted)
                OutlinedTextField(
                    value = code,
                    onValueChange = { code = it.filter(Char::isDigit).take(6) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("کد ورود") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    singleLine = true,
                )
                if (state.devCode != null) Text("کد توسعه: ${state.devCode}", color = Muted, fontSize = 11.sp)
                PrimaryButton("ورود به Velo") { vm.verifyOtp(code) { nav.popBackStack() } }
                TextButton(onClick = { vm.clearNotice(); vm.requestOtp(state.pendingEmail) }) { Text("ارسال دوباره کد") }
            }

            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            state.info?.let { Text(it, color = VeloPurple) }
        }
    }
}
